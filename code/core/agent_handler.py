# Assuming logger is available
import json
import traceback
from agent.langgraph_agent import run_agent
from utils.logger import get_logger, LogLevel

logger = get_logger(__name__)

async def handle_agent_request(query_params, body, send_response, send_chunk, streaming=False):
    """
    Handle an NLWeb Agent request by processing it with NLWebHandler
    
    Args:
        query_params (dict): URL query parameters
        body (bytes): Request body
        send_response (callable): Function to send response headers
        send_chunk (callable): Function to send response body
        streaming (bool, optional): Whether to use streaming response
    """
    try:
        # Parse the request body as JSON
        if body:
            try:
                request_data = json.loads(body)
                
                # Extract the function call details
                query = request_data.get("query", "")
                thread_id = request_data.get("thread_id", "")
                
                if not query:
                    # Return error for unsupported functions
                    error_response = {
                        "type": "agent_response",
                        "status": "error",
                        "error": f"Unknown query: {query}"
                    }
                    await send_response(400, {'Content-Type': 'application/json'})
                    await send_chunk(json.dumps(error_response), end_response=True)
                    return
                else:
                    result = await run_agent(query, thread_id)
                    agent_response = {
                        "type": "agent_response",
                        "status": "success",
                        "response": {
                            "result": result
                        }
                    }
                    # Send the response
                    await send_response(200, {'Content-Type': 'application/json'})
                    await send_chunk(json.dumps(agent_response), end_response=True)
                
            except json.JSONDecodeError as e:
                logger.error(f"Invalid JSON in NLWeb Agent request: {e}")
                print(f"Invalid JSON in NLWeb Agent request: {e}")
                await send_response(400, {'Content-Type': 'application/json'})
                await send_chunk(json.dumps({
                    "type": "agent_response",
                    "status": "error",
                    "error": f"Invalid JSON: {str(e)}"
                }), end_response=True)
        else:
            logger.error("Empty NLWeb Agent request body")
            print("Empty NLWeb Agent request body")
            await send_response(400, {'Content-Type': 'application/json'})
            await send_chunk(json.dumps({
                "type": "agent_response",
                "status": "error",
                "error": "Empty request body"
            }), end_response=True)
            
    except Exception as e:
        logger.error(f"Error processing NLWeb Agent request: {e}", exc_info=True)
        print(f"Error processing NLWeb Agent request: {e}\n{traceback.format_exc()}")
        await send_response(500, {'Content-Type': 'application/json'})
        await send_chunk(json.dumps({
            "type": "agent_response",
            "status": "error",
            "error": f"Internal server error: {str(e)}"
        }), end_response=True)