"""
Example demonstrating how to set up and use the DevTeam Manager.

This example shows how to:
1. Register the DevTeam Manager with the manager registry
2. Submit tasks to the DevTeam
3. Monitor progress and receive completion notifications
4. Handle events and status updates
"""

import asyncio
import logging
from typing import Any, Dict

from pythonium.core.managers import get_manager_registry
from pythonium.common.events import get_event_manager
from pythonium.common.config import get_settings
from pythonium.managers import DevTeamManager
from pythonium.managers.devteam_events import DevTeamEvents, TaskType, TaskPriority


# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class DevTeamExample:
    """Example demonstrating DevTeam Manager usage."""
    
    def __init__(self):
        self.manager_registry = get_manager_registry()
        self.event_manager = get_event_manager()
        self.devteam_manager = None
        self.task_results = {}
        
    async def setup(self):
        """Set up the DevTeam Manager and event handlers."""
        logger.info("Setting up DevTeam Manager example")
        
        # Initialize event manager
        await self.event_manager.initialize()
        
        # Register the DevTeam Manager
        self.manager_registry.register_manager(
            "devteam",
            DevTeamManager,
            auto_start=True,
            priority=50
        )
        
        # Set up manager registry with event manager
        self.manager_registry.set_event_manager(self.event_manager)
        self.manager_registry.set_config_manager(get_settings())
        
        # Start all managers
        await self.manager_registry.start_all_managers()
        
        # Get the DevTeam manager instance
        self.devteam_manager = await self.manager_registry.get_manager("devteam")
        
        if not self.devteam_manager:
            raise RuntimeError("Failed to get DevTeam manager")
            
        # Set up event handlers
        await self._setup_event_handlers()
        
        logger.info("DevTeam Manager setup complete")
    
    async def _setup_event_handlers(self):
        """Set up event handlers for DevTeam events."""
        
        # Handle task submissions
        self.event_manager.subscribe(
            DevTeamEvents.TASK_SUBMITTED,
            self._handle_task_submitted
        )
        
        # Handle task progress updates
        self.event_manager.subscribe(
            DevTeamEvents.TASK_PROGRESS,
            self._handle_task_progress
        )
        
        # Handle task completion
        self.event_manager.subscribe(
            DevTeamEvents.TASK_COMPLETED,
            self._handle_task_completed
        )
        
        # Handle task failures
        self.event_manager.subscribe(
            DevTeamEvents.TASK_FAILED,
            self._handle_task_failed
        )
        
        logger.info("Event handlers set up")
    
    async def _handle_task_submitted(self, event):
        """Handle task submission events."""
        data = event.data
        task_id = data.get('task_id', 'unknown')
        logger.info(f"✓ Task {task_id} submitted successfully")
    
    async def _handle_task_progress(self, event):
        """Handle task progress events."""
        data = event.data
        task_id = data.get('task_id', 'unknown')
        progress = data.get('percentage_complete', 0)
        phase = data.get('phase', 'unknown')
        current_agent = data.get('current_agent', 'unknown')
        
        logger.info(f"📊 Task {task_id}: {progress:.1f}% complete - {phase} (Agent: {current_agent})")
        
        # Show recent accomplishments
        accomplishments = data.get('recent_accomplishments', [])
        if accomplishments:
            logger.info(f"   Recent: {', '.join(accomplishments)}")
    
    async def _handle_task_completed(self, event):
        """Handle task completion events."""
        data = event.data
        task_id = data.get('task_id', 'unknown')
        status = data.get('status', 'unknown')
        summary = data.get('summary', 'No summary available')
        
        logger.info(f"✅ Task {task_id} completed with status: {status}")
        logger.info(f"   Summary: {summary}")
        
        # Store results
        self.task_results[task_id] = data
        
        # Show deliverables
        deliverables = data.get('deliverables', [])
        if deliverables:
            logger.info("   Deliverables:")
            for deliverable in deliverables:
                logger.info(f"     - {deliverable.get('type', 'unknown')}: {deliverable.get('description', 'No description')}")
    
    async def _handle_task_failed(self, event):
        """Handle task failure events."""
        data = event.data
        task_id = data.get('task_id', 'unknown')
        error = data.get('error', 'Unknown error')
        
        logger.error(f"❌ Task {task_id} failed: {error}")
        
        # Store failure info
        self.task_results[task_id] = data
    
    async def submit_feature_task(self) -> str:
        """Submit a sample feature development task."""
        task_data = {
            'task_id': 'feature-auth-001',
            'task_type': 'feature',
            'title': 'User Authentication System',
            'description': 'Implement a comprehensive user authentication system with JWT tokens and MFA support',
            'submitter': 'demo_client',
            'priority': 'high',
            'requirements': [
                'JWT token-based authentication',
                'Password reset functionality',
                'Multi-factor authentication support',
                'User session management'
            ],
            'tags': ['authentication', 'security', 'user-management']
        }
        
        # Submit the task
        await self.event_manager.publish(
            "devteam.task.submit",
            task_data,
            source="demo_client"
        )
        
        logger.info(f"Submitted feature task: {task_data['task_id']}")
        return task_data['task_id']
    
    async def submit_bugfix_task(self) -> str:
        """Submit a sample bug fix task."""
        task_data = {
            'task_id': 'bugfix-memory-001',
            'task_type': 'bugfix',
            'title': 'Fix Memory Leak in Session Handler',
            'description': 'Memory leak detected in user session handler causing server instability',
            'submitter': 'demo_client',
            'priority': 'urgent',
            'requirements': [
                'Identify source of memory leak',
                'Fix memory management issues',
                'Add memory usage monitoring',
                'Ensure no regression'
            ],
            'tags': ['bug', 'memory', 'performance']
        }
        
        # Submit the task
        await self.event_manager.publish(
            "devteam.task.submit",
            task_data,
            source="demo_client"
        )
        
        logger.info(f"Submitted bugfix task: {task_data['task_id']}")
        return task_data['task_id']
    
    async def show_team_status(self):
        """Display current team status."""
        if not self.devteam_manager:
            logger.error("DevTeam manager not available")
            return
            
        status = self.devteam_manager.get_team_status()
        
        logger.info("📋 DevTeam Status:")
        logger.info(f"   Active tasks: {status['active_tasks']}")
        logger.info(f"   Queued tasks: {status['queued_tasks']}")
        logger.info(f"   Total tasks: {status['total_tasks']}")
        logger.info(f"   Agents: {len(status['agents'])}")
        
        # Show agent details
        for agent_id, agent_info in status['agents'].items():
            logger.info(f"     {agent_id}: {agent_info['status']} ({agent_info['current_tasks']}/{agent_info['max_tasks']} tasks)")
    
    async def wait_for_task_completion(self, task_id: str, timeout: float = 60.0):
        """Wait for a specific task to complete."""
        start_time = asyncio.get_event_loop().time()
        
        while asyncio.get_event_loop().time() - start_time < timeout:
            if task_id in self.task_results:
                return self.task_results[task_id]
            await asyncio.sleep(1.0)
        
        raise asyncio.TimeoutError(f"Task {task_id} did not complete within {timeout} seconds")
    
    async def run_demo(self):
        """Run the complete demonstration."""
        logger.info("🚀 Starting DevTeam Manager Demo")
        
        try:
            # Show initial status
            await self.show_team_status()
            
            # Submit tasks
            logger.info("\n📝 Submitting development tasks...")
            feature_task_id = await self.submit_feature_task()
            await asyncio.sleep(1)  # Brief delay between submissions
            
            bugfix_task_id = await self.submit_bugfix_task()
            await asyncio.sleep(2)  # Allow processing to start
            
            # Show updated status
            logger.info("\n📊 Updated team status after task submission:")
            await self.show_team_status()
            
            # Wait for tasks to complete (with timeout)
            logger.info(f"\n⏳ Waiting for tasks to complete...")
            
            try:
                # Wait for feature task
                feature_result = await self.wait_for_task_completion(feature_task_id, timeout=30.0)
                logger.info(f"Feature task completed: {feature_result.get('status', 'unknown')}")
                
                # Wait for bugfix task  
                bugfix_result = await self.wait_for_task_completion(bugfix_task_id, timeout=30.0)
                logger.info(f"Bugfix task completed: {bugfix_result.get('status', 'unknown')}")
                
            except asyncio.TimeoutError as e:
                logger.warning(f"Timeout waiting for task completion: {e}")
            
            # Final status
            logger.info("\n📋 Final team status:")
            await self.show_team_status()
            
            logger.info("\n✅ Demo completed successfully")
            
        except Exception as e:
            logger.error(f"Demo failed: {e}")
            raise
    
    async def cleanup(self):
        """Clean up resources."""
        logger.info("Cleaning up...")
        
        # Stop all managers
        await self.manager_registry.shutdown_all()
        
        # Shutdown event manager
        await self.event_manager.shutdown()
        
        logger.info("Cleanup complete")


async def main():
    """Main function to run the DevTeam Manager example."""
    demo = DevTeamExample()
    
    try:
        # Set up the demo
        await demo.setup()
        
        # Run the demonstration
        await demo.run_demo()
        
    except Exception as e:
        logger.error(f"Example failed: {e}")
        raise
    
    finally:
        # Clean up
        await demo.cleanup()


if __name__ == "__main__":
    # Run the example
    asyncio.run(main())