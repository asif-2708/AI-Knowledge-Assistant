from mcp.server.fastmcp import FastMCP
from ..database.database import SessionLocal
from ..services.chat_service import ChatService
from ..database.models import User

# Initialize FastMCP Server
mcp_server = FastMCP("AI Knowledge Assistant MCP")


@mcp_server.tool()
def search_documents(query: str) -> str:
    """Search uploaded documents for relevant text snippets based on a semantic search query."""
    db = SessionLocal()
    try:
        service = ChatService(db)
        
        # Look up first user as default context for search
        user = db.query(User).first()
        user_id = user.id if user else 1
        
        chunks = service.retrieve_relevant_chunks(query, user_id=user_id, limit=8)
        if not chunks:
            return "No matching document snippets found."
        
        return "\n\n".join([f"[{chunk.document.filename}]: {chunk.text}" for chunk in chunks])
    except Exception as e:
        return f"Error searching documents: {str(e)}"
    finally:
        db.close()


@mcp_server.tool()
def summarize_text(text: str) -> str:
    """Summarize a block of text into concise bullet points."""
    db = SessionLocal()
    try:
        service = ChatService(db)
        return service.summarize_text(text)
    except Exception as e:
        return f"Error summarizing text: {str(e)}"
    finally:
        db.close()
