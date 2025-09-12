"""
Agent routing and execution module
"""

from typing import Dict, Any, List, Literal, Optional
import logging
from langgraph.runtime import Runtime
from langgraph.types import Send
from langchain_core.messages import AIMessage

from ...schemas.context import AgentContext
from ...schemas.state import AgentState

logger = logging.getLogger(__name__)


class AgentExecutor:
    """에이전트 라우팅 및 실행 관리"""
    
    def route_agents(
        self,
        state: AgentState,
        runtime: Runtime[AgentContext]
    ) -> Dict[str, Any]:
        """에이전트 라우팅 및 실행"""
        logger.info("Routing to agents")
        
        plan = state.get("execution_plan", [])
        current_step = self._get_next_step(plan, state)
        
        if not current_step:
            return {"workflow_status": "completed"}
        
        agent_name = current_step["agent_name"]
        
        # 병렬 실행 처리
        parallel_agents = []
        if runtime.context.parallel_execution and current_step.get("parallel"):
            parallel_agents = self._get_parallel_agents(plan, current_step, state)
        
        # Send 메커니즘
        sends = self._create_sends(agent_name, parallel_agents, state, runtime.context)
        
        # 에이전트 시퀀스 업데이트
        executed_agents = [agent_name] + [a["agent_name"] for a in parallel_agents]
        
        return {
            "current_agent": agent_name,
            "agent_sequence": state.get("agent_sequence", []) + executed_agents,
            "messages": [
                AIMessage(content=f"실행 중: {', '.join(executed_agents)}")
            ]
        }
    
    def check_completion(
        self, 
        state: AgentState
    ) -> Literal["continue", "aggregate", "error"]:
        """완료 상태 확인"""
        if state.get("errors"):
            return "error"
        
        plan = state.get("execution_plan", [])
        executed = state.get("agent_sequence", [])
        
        planned_agents = [step["agent_name"] for step in plan]
        if all(agent in executed for agent in planned_agents):
            return "aggregate"
        
        return "continue"
    
    def _get_next_step(
        self, 
        plan: List[Dict], 
        state: AgentState
    ) -> Optional[Dict]:
        """다음 실행할 단계 찾기"""
        executed = state.get("agent_sequence", [])
        for step in plan:
            if step["agent_name"] not in executed:
                deps = step.get("dependencies", [])
                if all(d in executed for d in deps):
                    return step
        return None
    
    def _get_parallel_agents(
        self, 
        plan: List[Dict], 
        current_step: Dict,
        state: AgentState
    ) -> List[Dict]:
        """병렬 실행 가능한 에이전트 찾기"""
        parallel = []
        executed = state.get("agent_sequence", [])
        
        for step in plan:
            if (step != current_step and 
                step.get("parallel") and 
                step["agent_name"] not in executed):
                parallel.append(step)
        return parallel
    
    def _create_sends(
        self,
        agent_name: str,
        parallel_agents: List[Dict],
        state: AgentState,
        context: AgentContext
    ) -> List[Send]:
        """Send 객체 생성"""
        sends = []
        
        if parallel_agents:
            # 병렬 실행
            for agent in parallel_agents:
                sends.append(Send(f"{agent['agent_name']}_agent", {
                    "state": state,
                    "context": context
                }))
        else:
            # 단일 실행
            sends.append(Send(f"{agent_name}_agent", {
                "state": state,
                "context": context
            }))
        
        return sends