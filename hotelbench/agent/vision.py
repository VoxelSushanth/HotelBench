"""
HotelBench Vision Module
Screenshot → Claude Vision → Action Plan
"""

import json
import base64
from typing import Optional
from anthropic import Anthropic
from config import ANTHROPIC_API_KEY, CLAUDE_MODEL, MIN_CONFIDENCE_THRESHOLD
from agent.prompts import SYSTEM_PROMPT, get_user_prompt


class VisionReasoner:
    """Claude Vision API client for screenshot analysis and action planning."""
    
    def __init__(self, api_key: str = ANTHROPIC_API_KEY, model: str = CLAUDE_MODEL):
        self.client = Anthropic(api_key=api_key)
        self.model = model
    
    async def analyze_screenshot(
        self,
        screenshot_base64: str,
        task_description: str,
        current_tab: str,
        action_history: list
    ) -> dict:
        """
        Analyze a screenshot and return the next action plan.
        
        Args:
            screenshot_base64: Base64-encoded PNG screenshot
            task_description: Natural language task description
            current_tab: Current active tab in PMS UI
            action_history: List of previously executed actions
        
        Returns:
            dict with observation, reasoning, action, confidence, task_complete, completion_note
        """
        user_prompt = get_user_prompt(task_description, current_tab, action_history)
        
        try:
            response = self.client.messages.create(
                model=self.model,
                max_tokens=1024,
                system=SYSTEM_PROMPT,
                messages=[
                    {
                        "role": "user",
                        "content": [
                            {
                                "type": "image",
                                "source": {
                                    "type": "base64",
                                    "media_type": "image/png",
                                    "data": screenshot_base64
                                }
                            },
                            {
                                "type": "text",
                                "text": user_prompt
                            }
                        ]
                    }
                ]
            )
            
            # Parse the response
            text_content = response.content[0].text
            
            # Extract JSON from response (handle potential markdown wrapping)
            json_str = self._extract_json(text_content)
            
            if json_str:
                plan = json.loads(json_str)
                
                # Validate required fields
                required_fields = ["observation", "reasoning", "action", "confidence", "task_complete"]
                for field in required_fields:
                    if field not in plan:
                        plan[field] = None if field in ["completion_note"] else ""
                        if field == "action":
                            plan[field] = {"type": "", "target": "", "value": ""}
                        elif field == "confidence":
                            plan[field] = 0.5
                        elif field == "task_complete":
                            plan[field] = False
                
                # Ensure action has required structure
                if not isinstance(plan["action"], dict):
                    plan["action"] = {"type": "", "target": "", "value": ""}
                
                # If confidence is below threshold, override with scroll action
                if plan.get("confidence", 0) < MIN_CONFIDENCE_THRESHOLD:
                    plan["action"]["type"] = "scroll"
                    plan["action"]["target"] = ""
                    plan["action"]["value"] = ""
                    plan["reasoning"] = "Low confidence - scrolling to reveal more UI context"
                
                return plan
            else:
                return self._get_fallback_response("Failed to parse JSON from Claude response")
                
        except json.JSONDecodeError as e:
            return self._get_fallback_response(f"JSON parsing error: {str(e)}")
        except Exception as e:
            return self._get_fallback_response(f"Claude API error: {str(e)}")
    
    def _extract_json(self, text: str) -> Optional[str]:
        """Extract JSON from text, handling potential markdown wrapping."""
        text = text.strip()
        
        # Try to parse directly first
        try:
            json.loads(text)
            return text
        except json.JSONDecodeError:
            pass
        
        # Look for JSON within markdown code blocks
        if "```json" in text:
            start = text.find("```json") + 7
            end = text.find("```", start)
            if end > start:
                return text[start:end].strip()
        
        # Look for JSON within generic code blocks
        if "```" in text:
            start = text.find("```") + 3
            end = text.find("```", start)
            if end > start:
                return text[start:end].strip()
        
        # Try to find JSON by looking for opening/closing braces
        brace_count = 0
        start_idx = None
        for i, char in enumerate(text):
            if char == '{':
                if start_idx is None:
                    start_idx = i
                brace_count += 1
            elif char == '}':
                brace_count -= 1
                if brace_count == 0 and start_idx is not None:
                    return text[start_idx:i+1]
        
        return None
    
    def _get_fallback_response(self, error_message: str) -> dict:
        """Return a safe fallback response when parsing fails."""
        return {
            "observation": "Unable to analyze screenshot due to error",
            "reasoning": error_message,
            "action": {
                "type": "scroll",
                "target": "",
                "value": ""
            },
            "confidence": 0.3,
            "task_complete": False,
            "completion_note": ""
        }


# Global vision reasoner instance
_vision_reasoner: Optional[VisionReasoner] = None


def get_vision_reasoner() -> VisionReasoner:
    """Get or create the global vision reasoner instance."""
    global _vision_reasoner
    if _vision_reasoner is None:
        _vision_reasoner = VisionReasoner()
    return _vision_reasoner
