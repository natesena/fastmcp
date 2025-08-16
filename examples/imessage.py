"""
iMessage MCP Server - Read messages from the local iMessages database

HOW TO RUN THIS SERVER:
----------------------
1. Open Terminal
2. Navigate to the FastMCP directory:
   cd /Users/nathanielsena/Documents/code/build_the_future_mcp/fastmcp

3. Install dependencies (if not already installed):
   pip install -e .

4. Run the server:

   For HTTP Server (direct API access):
   python examples/imessage.py
   
   The server will run on http://localhost:8008/mcp
   You can test it with: curl http://localhost:8008/mcp
   
   For STDIO mode (MCP client integration like Claude Desktop):
   fastmcp run examples/imessage.py

REQUIREMENTS:
- Python 3.10+
- Access to ~/Library/Messages/chat.db (macOS iMessage database)
- FastMCP installed (pip install -e .)

NOTES:
- The server reads your local iMessage database in read-only mode
- No messages are modified or deleted
- Configure IMESSAGES_DB_PATH environment variable to use a different database location
"""

import os
import sqlite3
from datetime import datetime
from pathlib import Path
from typing import Optional
from dotenv import load_dotenv

from fastmcp import FastMCP

# Load environment variables
load_dotenv()

# Get the database path from environment variable
IMESSAGES_DB_PATH = os.getenv("IMESSAGES_DB_PATH", str(Path.home() / "Library/Messages/chat.db"))

mcp = FastMCP("iMessage Server")


def get_db_connection():
    """Create a read-only connection to the iMessages database"""
    if not os.path.exists(IMESSAGES_DB_PATH):
        raise FileNotFoundError(f"iMessages database not found at {IMESSAGES_DB_PATH}")
    
    # Connect with read-only mode
    conn = sqlite3.connect(f"file:{IMESSAGES_DB_PATH}?mode=ro", uri=True)
    conn.row_factory = sqlite3.Row
    return conn


@mcp.tool
def get_recent_messages(limit: int = 20) -> list[dict]:
    """Get the most recent messages from iMessages"""
    conn = get_db_connection()
    try:
        cursor = conn.cursor()
        query = """
        SELECT 
            m.guid,
            m.text,
            m.is_from_me,
            datetime(m.date/1000000000 + strftime('%s', '2001-01-01'), 'unixepoch', 'localtime') as date,
            h.id as contact
        FROM message m
        LEFT JOIN handle h ON m.handle_id = h.ROWID
        WHERE m.text IS NOT NULL
        ORDER BY m.date DESC
        LIMIT ?
        """
        cursor.execute(query, (limit,))
        messages = []
        for row in cursor.fetchall():
            messages.append({
                "guid": row["guid"],
                "text": row["text"],
                "is_from_me": bool(row["is_from_me"]),
                "date": row["date"],
                "contact": row["contact"]
            })
        return messages
    finally:
        conn.close()


@mcp.tool
def search_messages(search_term: str, limit: int = 50) -> list[dict]:
    """Search for messages containing specific text"""
    conn = get_db_connection()
    try:
        cursor = conn.cursor()
        query = """
        SELECT 
            m.guid,
            m.text,
            m.is_from_me,
            datetime(m.date/1000000000 + strftime('%s', '2001-01-01'), 'unixepoch', 'localtime') as date,
            h.id as contact
        FROM message m
        LEFT JOIN handle h ON m.handle_id = h.ROWID
        WHERE m.text LIKE ?
        ORDER BY m.date DESC
        LIMIT ?
        """
        cursor.execute(query, (f"%{search_term}%", limit))
        messages = []
        for row in cursor.fetchall():
            messages.append({
                "guid": row["guid"],
                "text": row["text"],
                "is_from_me": bool(row["is_from_me"]),
                "date": row["date"],
                "contact": row["contact"]
            })
        return messages
    finally:
        conn.close()


@mcp.tool
def get_messages_from_contact(contact: str, limit: int = 50) -> list[dict]:
    """Get messages from a specific contact (phone number or email)"""
    conn = get_db_connection()
    try:
        cursor = conn.cursor()
        query = """
        SELECT 
            m.guid,
            m.text,
            m.is_from_me,
            datetime(m.date/1000000000 + strftime('%s', '2001-01-01'), 'unixepoch', 'localtime') as date,
            h.id as contact
        FROM message m
        LEFT JOIN handle h ON m.handle_id = h.ROWID
        WHERE h.id LIKE ? AND m.text IS NOT NULL
        ORDER BY m.date DESC
        LIMIT ?
        """
        cursor.execute(query, (f"%{contact}%", limit))
        messages = []
        for row in cursor.fetchall():
            messages.append({
                "guid": row["guid"],
                "text": row["text"],
                "is_from_me": bool(row["is_from_me"]),
                "date": row["date"],
                "contact": row["contact"]
            })
        return messages
    finally:
        conn.close()


@mcp.tool
def get_conversation_list(limit: int = 20) -> list[dict]:
    """Get a list of recent conversations with contact names and last message"""
    conn = get_db_connection()
    try:
        cursor = conn.cursor()
        query = """
        SELECT 
            c.chat_identifier,
            c.display_name,
            MAX(m.date) as last_message_date,
            COUNT(m.ROWID) as message_count,
            (SELECT text FROM message WHERE handle_id = h.ROWID ORDER BY date DESC LIMIT 1) as last_message
        FROM chat c
        JOIN chat_message_join cmj ON c.ROWID = cmj.chat_id
        JOIN message m ON cmj.message_id = m.ROWID
        LEFT JOIN chat_handle_join chj ON c.ROWID = chj.chat_id
        LEFT JOIN handle h ON chj.handle_id = h.ROWID
        GROUP BY c.ROWID
        ORDER BY last_message_date DESC
        LIMIT ?
        """
        cursor.execute(query, (limit,))
        conversations = []
        for row in cursor.fetchall():
            conversations.append({
                "chat_id": row["chat_identifier"],
                "display_name": row["display_name"] or row["chat_identifier"],
                "last_message_date": datetime.fromtimestamp(row["last_message_date"]/1000000000 + 978307200).isoformat() if row["last_message_date"] else None,
                "message_count": row["message_count"],
                "last_message": row["last_message"]
            })
        return conversations
    finally:
        conn.close()


@mcp.tool
def get_message_stats() -> dict:
    """Get statistics about the messages database"""
    conn = get_db_connection()
    try:
        cursor = conn.cursor()
        
        # Total messages
        cursor.execute("SELECT COUNT(*) as total FROM message WHERE text IS NOT NULL")
        total_messages = cursor.fetchone()["total"]
        
        # Messages sent vs received
        cursor.execute("SELECT COUNT(*) as sent FROM message WHERE is_from_me = 1 AND text IS NOT NULL")
        sent_messages = cursor.fetchone()["sent"]
        
        # Total unique contacts
        cursor.execute("SELECT COUNT(DISTINCT handle_id) as contacts FROM message")
        total_contacts = cursor.fetchone()["contacts"]
        
        # Total conversations
        cursor.execute("SELECT COUNT(*) as chats FROM chat")
        total_chats = cursor.fetchone()["chats"]
        
        return {
            "total_messages": total_messages,
            "sent_messages": sent_messages,
            "received_messages": total_messages - sent_messages,
            "total_contacts": total_contacts,
            "total_conversations": total_chats
        }
    finally:
        conn.close()


@mcp.tool
def get_message(message_id: int) -> dict:
    """Get a specific message by its ID"""
    conn = get_db_connection()
    try:
        cursor = conn.cursor()
        query = """
        SELECT 
            message.ROWID as id,
            message.text,
            message.attributedBody,
            datetime(message.date/1000000000 + strftime('%s', '2001-01-01'), 'unixepoch', 'localtime') as date,
            message.is_from_me,
            handle.id as sender_id,
            handle.id as sender_name
        FROM message 
        JOIN chat_message_join ON chat_message_join.message_id = message.ROWID
        JOIN chat ON chat.ROWID = chat_message_join.chat_id
        LEFT JOIN handle ON message.handle_id = handle.ROWID
        WHERE message.ROWID = ?
        """
        cursor.execute(query, (message_id,))
        row = cursor.fetchone()
        if row:
            return dict(row)
        return None
    finally:
        conn.close()


@mcp.tool
def get_message_count(chat_id: str) -> int:
    """Get the total number of messages in a chat"""
    conn = get_db_connection()
    try:
        cursor = conn.cursor()
        query = """
        SELECT COUNT(*) as count
        FROM message 
        JOIN chat_message_join ON chat_message_join.message_id = message.ROWID
        WHERE chat_message_join.chat_id = ?
        """
        cursor.execute(query, (chat_id,))
        return cursor.fetchone()["count"]
    finally:
        conn.close()


@mcp.tool
def get_messages(chat_id: int, limit: int = 50, offset: int = 0, order: str = "DESC") -> list[dict]:
    """Get messages from a specific chat with pagination"""
    conn = get_db_connection()
    try:
        cursor = conn.cursor()
        query = f"""
        SELECT 
            message.ROWID as id,
            message.text,
            message.attributedBody,
            datetime(message.date/1000000000 + strftime('%s', '2001-01-01'), 'unixepoch', 'localtime') as date,
            message.is_from_me,
            handle.id as sender_id,
            handle.id as sender_name
        FROM message 
        JOIN chat_message_join ON chat_message_join.message_id = message.ROWID
        JOIN chat ON chat.ROWID = chat_message_join.chat_id
        LEFT JOIN handle ON message.handle_id = handle.ROWID
        WHERE chat_message_join.chat_id = ?
        ORDER BY message.date {order}
        LIMIT ? OFFSET ?
        """
        cursor.execute(query, (chat_id, limit, offset))
        return [dict(row) for row in cursor.fetchall()]
    finally:
        conn.close()


@mcp.tool
def get_messages_before(chat_id: int, message_id: int, limit: int = 50) -> list[dict]:
    """Get messages from a chat before a specific message ID"""
    conn = get_db_connection()
    try:
        cursor = conn.cursor()
        query = """
        SELECT 
            message.ROWID as id,
            message.text,
            message.attributedBody,
            datetime(message.date/1000000000 + strftime('%s', '2001-01-01'), 'unixepoch', 'localtime') as date,
            message.is_from_me,
            handle.id as sender_id,
            handle.id as sender_name
        FROM message 
        JOIN chat_message_join ON chat_message_join.message_id = message.ROWID
        JOIN chat ON chat.ROWID = chat_message_join.chat_id
        LEFT JOIN handle ON message.handle_id = handle.ROWID
        WHERE chat_message_join.chat_id = ?
        AND message.ROWID < ?
        ORDER BY message.date ASC
        LIMIT ?
        """
        cursor.execute(query, (chat_id, message_id, limit))
        return [dict(row) for row in cursor.fetchall()]
    finally:
        conn.close()


@mcp.tool
def get_messages_after_id(chat_id: int, message_id: int, limit: int = 50) -> list[dict]:
    """Get messages from a chat after a specific message ID"""
    conn = get_db_connection()
    try:
        cursor = conn.cursor()
        query = """
        SELECT 
            message.ROWID as id,
            message.text,
            message.attributedBody,
            datetime(message.date/1000000000 + strftime('%s', '2001-01-01'), 'unixepoch', 'localtime') as date,
            message.is_from_me,
            handle.id as sender_id,
            handle.id as sender_name
        FROM message 
        JOIN chat_message_join ON chat_message_join.message_id = message.ROWID
        JOIN chat ON chat.ROWID = chat_message_join.chat_id
        LEFT JOIN handle ON message.handle_id = handle.ROWID
        WHERE chat_message_join.chat_id = ?
        AND message.ROWID > ?
        ORDER BY message.date ASC
        LIMIT ?
        """
        cursor.execute(query, (chat_id, message_id, limit))
        return [dict(row) for row in cursor.fetchall()]
    finally:
        conn.close()


@mcp.tool
def get_messages_before_date(chat_id: int, date: str, limit: int = 50) -> list[dict]:
    """Get messages from a chat before a specific date (Apple epoch timestamp)"""
    conn = get_db_connection()
    try:
        cursor = conn.cursor()
        # Convert ISO date to Apple epoch if needed
        if isinstance(date, str) and "-" in date:
            # Convert from ISO format to Apple epoch
            from datetime import datetime
            dt = datetime.fromisoformat(date.replace('Z', '+00:00'))
            apple_epoch = int((dt.timestamp() - 978307200) * 1000000000)
        else:
            apple_epoch = int(date)
        
        query = """
        SELECT 
            message.ROWID as id,
            message.text,
            message.attributedBody,
            datetime(message.date/1000000000 + strftime('%s', '2001-01-01'), 'unixepoch', 'localtime') as date,
            message.is_from_me,
            handle.id as sender_id,
            handle.id as sender_name
        FROM message 
        JOIN chat_message_join ON chat_message_join.message_id = message.ROWID
        JOIN chat ON chat.ROWID = chat_message_join.chat_id
        LEFT JOIN handle ON message.handle_id = handle.ROWID
        WHERE chat_message_join.chat_id = ?
        AND message.date < ?
        ORDER BY message.date DESC
        LIMIT ?
        """
        cursor.execute(query, (chat_id, apple_epoch, limit))
        return [dict(row) for row in cursor.fetchall()]
    finally:
        conn.close()


@mcp.tool
def get_messages_after_date(chat_id: int, date: str, limit: int = 50) -> list[dict]:
    """Get messages from a chat after a specific date (Apple epoch timestamp)"""
    conn = get_db_connection()
    try:
        cursor = conn.cursor()
        # Convert ISO date to Apple epoch if needed
        if isinstance(date, str) and "-" in date:
            # Convert from ISO format to Apple epoch
            from datetime import datetime
            dt = datetime.fromisoformat(date.replace('Z', '+00:00'))
            apple_epoch = int((dt.timestamp() - 978307200) * 1000000000)
        else:
            apple_epoch = int(date)
        
        query = """
        SELECT 
            message.ROWID as id,
            message.text,
            message.attributedBody,
            datetime(message.date/1000000000 + strftime('%s', '2001-01-01'), 'unixepoch', 'localtime') as date,
            message.is_from_me,
            handle.id as sender_id,
            handle.id as sender_name
        FROM message 
        JOIN chat_message_join ON chat_message_join.message_id = message.ROWID
        JOIN chat ON chat.ROWID = chat_message_join.chat_id
        LEFT JOIN handle ON message.handle_id = handle.ROWID
        WHERE chat_message_join.chat_id = ?
        AND message.date > ?
        ORDER BY message.date ASC
        LIMIT ?
        """
        cursor.execute(query, (chat_id, apple_epoch, limit))
        return [dict(row) for row in cursor.fetchall()]
    finally:
        conn.close()


@mcp.tool
def get_messages_same_date(chat_id: int, date: str) -> list[dict]:
    """Get all messages from a chat on a specific date (Apple epoch timestamp)"""
    conn = get_db_connection()
    try:
        cursor = conn.cursor()
        # Convert ISO date to Apple epoch if needed
        if isinstance(date, str) and "-" in date:
            # Convert from ISO format to Apple epoch
            from datetime import datetime
            dt = datetime.fromisoformat(date.replace('Z', '+00:00'))
            apple_epoch = int((dt.timestamp() - 978307200) * 1000000000)
        else:
            apple_epoch = int(date)
        
        query = """
        SELECT 
            message.ROWID as id,
            message.text,
            message.attributedBody,
            datetime(message.date/1000000000 + strftime('%s', '2001-01-01'), 'unixepoch', 'localtime') as date,
            message.is_from_me,
            handle.id as sender_id,
            handle.id as sender_name
        FROM message 
        JOIN chat_message_join ON chat_message_join.message_id = message.ROWID
        JOIN chat ON chat.ROWID = chat_message_join.chat_id
        LEFT JOIN handle ON message.handle_id = handle.ROWID
        WHERE chat_message_join.chat_id = ?
          AND message.date = ?
        ORDER BY message.ROWID ASC
        """
        cursor.execute(query, (chat_id, apple_epoch))
        return [dict(row) for row in cursor.fetchall()]
    finally:
        conn.close()


@mcp.tool
def get_unique_senders_since(date: str) -> int:
    """Get count of unique senders since a specific date (excluding yourself)"""
    conn = get_db_connection()
    try:
        cursor = conn.cursor()
        # Convert ISO date to Apple epoch if needed
        if isinstance(date, str) and "-" in date:
            # Convert from ISO format to Apple epoch
            from datetime import datetime
            dt = datetime.fromisoformat(date.replace('Z', '+00:00'))
            apple_epoch = int((dt.timestamp() - 978307200) * 1000000000)
        else:
            apple_epoch = int(date)
        
        query = """
        SELECT COUNT(DISTINCT handle.id) as count
        FROM message
        LEFT JOIN handle ON message.handle_id = handle.ROWID
        WHERE message.is_from_me = 0 AND message.date >= ?
        """
        cursor.execute(query, (apple_epoch,))
        return cursor.fetchone()["count"]
    finally:
        conn.close()


@mcp.tool
def get_distinct_senders_since(date: str) -> list[dict]:
    """Get distinct senders and their message counts since a specific date"""
    conn = get_db_connection()
    try:
        cursor = conn.cursor()
        # Convert ISO date to Apple epoch if needed
        if isinstance(date, str) and "-" in date:
            # Convert from ISO format to Apple epoch
            from datetime import datetime
            dt = datetime.fromisoformat(date.replace('Z', '+00:00'))
            apple_epoch = int((dt.timestamp() - 978307200) * 1000000000)
        else:
            apple_epoch = int(date)
        
        query = """
        SELECT handle.id as sender_id, COUNT(*) as messages
        FROM message
        LEFT JOIN handle ON message.handle_id = handle.ROWID
        WHERE message.is_from_me = 0 AND message.date >= ?
        GROUP BY handle.id
        ORDER BY messages DESC
        """
        cursor.execute(query, (apple_epoch,))
        return [dict(row) for row in cursor.fetchall()]
    finally:
        conn.close()


@mcp.tool
def get_chat_id_from_message(message_id: int) -> Optional[int]:
    """Get the chat ID associated with a specific message"""
    conn = get_db_connection()
    try:
        cursor = conn.cursor()
        query = """
        SELECT 
            chat_message_join.chat_id AS chatId
        FROM message
        JOIN chat_message_join ON chat_message_join.message_id = message.ROWID
        WHERE message.ROWID = ?
        """
        cursor.execute(query, (message_id,))
        row = cursor.fetchone()
        return row["chatId"] if row else None
    finally:
        conn.close()


@mcp.tool
def get_last_message_id_from_chat(chat_id: int) -> Optional[int]:
    """Get the ID of the last message in a chat"""
    conn = get_db_connection()
    try:
        cursor = conn.cursor()
        query = """
        SELECT 
            message.ROWID as lastMessageId
        FROM message 
        JOIN chat_message_join ON chat_message_join.message_id = message.ROWID
        WHERE chat_message_join.chat_id = ?
        ORDER BY message.date DESC, message.ROWID DESC
        LIMIT 1
        """
        cursor.execute(query, (chat_id,))
        row = cursor.fetchone()
        return row["lastMessageId"] if row else None
    finally:
        conn.close()


@mcp.tool
def get_last_message_date_from_chat(chat_id: int) -> Optional[str]:
    """Get the date of the last message in a chat"""
    conn = get_db_connection()
    try:
        cursor = conn.cursor()
        query = """
        SELECT 
            datetime(message.date/1000000000 + strftime('%s', '2001-01-01'), 'unixepoch', 'localtime') as lastMessageDate
        FROM message 
        JOIN chat_message_join ON chat_message_join.message_id = message.ROWID
        WHERE chat_message_join.chat_id = ?
        ORDER BY message.date DESC, message.ROWID DESC
        LIMIT 1
        """
        cursor.execute(query, (chat_id,))
        row = cursor.fetchone()
        return row["lastMessageDate"] if row else None
    finally:
        conn.close()


@mcp.tool
def get_chat_names(limit: int = 50, offset: int = 0) -> list[dict]:
    """Get a list of chats ordered by most recent"""
    conn = get_db_connection()
    try:
        cursor = conn.cursor()
        query = """
        SELECT *
        FROM chat
        ORDER BY ROWID DESC
        LIMIT ? OFFSET ?
        """
        cursor.execute(query, (limit, offset))
        return [dict(row) for row in cursor.fetchall()]
    finally:
        conn.close()


@mcp.tool
def get_total_chat_count() -> int:
    """Get the total number of chats"""
    conn = get_db_connection()
    try:
        cursor = conn.cursor()
        query = """
        SELECT COUNT(*) as total
        FROM chat
        """
        cursor.execute(query)
        return cursor.fetchone()["total"]
    finally:
        conn.close()


@mcp.tool
def get_chat_participant_handles(chat_id: int) -> list[str]:
    """Get participant handles (phone numbers/emails) for a given chat"""
    conn = get_db_connection()
    try:
        cursor = conn.cursor()
        query = """
        SELECT h.id AS handle
        FROM chat_handle_join chj
        JOIN handle h ON h.ROWID = chj.handle_id
        WHERE chj.chat_id = ?
        """
        cursor.execute(query, (chat_id,))
        return [row["handle"] for row in cursor.fetchall()]
    finally:
        conn.close()


@mcp.tool
def get_chat_by_id(chat_id: int) -> Optional[dict]:
    """Get a single chat by its ROWID"""
    conn = get_db_connection()
    try:
        cursor = conn.cursor()
        query = """
        SELECT * FROM chat WHERE ROWID = ?
        """
        cursor.execute(query, (chat_id,))
        row = cursor.fetchone()
        return dict(row) if row else None
    finally:
        conn.close()


@mcp.tool
def get_chat_by_identifier(chat_identifier: str) -> Optional[dict]:
    """Get a single chat by its chat_identifier"""
    conn = get_db_connection()
    try:
        cursor = conn.cursor()
        query = """
        SELECT * FROM chat WHERE chat_identifier = ?
        """
        cursor.execute(query, (chat_identifier,))
        row = cursor.fetchone()
        return dict(row) if row else None
    finally:
        conn.close()


@mcp.tool
def get_handles(limit: int = 100) -> list[dict]:
    """Get a list of handles (contacts) with their phone numbers or emails"""
    conn = get_db_connection()
    try:
        cursor = conn.cursor()
        query = """
        SELECT 
            handle.ROWID as id,
            handle.id as phone_or_email,
            handle.service,
            handle.uncanonicalized_id
        FROM handle 
        LIMIT ?
        """
        cursor.execute(query, (limit,))
        return [dict(row) for row in cursor.fetchall()]
    finally:
        conn.close()


@mcp.tool
def get_handle_details(handle_id: int) -> Optional[dict]:
    """Get details for a specific handle by its ROWID"""
    conn = get_db_connection()
    try:
        cursor = conn.cursor()
        query = """
        SELECT 
            handle.ROWID as id,
            handle.id as phone_or_email,
            handle.service,
            handle.uncanonicalized_id
        FROM handle 
        WHERE handle.ROWID = ?
        """
        cursor.execute(query, (handle_id,))
        row = cursor.fetchone()
        return dict(row) if row else None
    finally:
        conn.close()


if __name__ == "__main__":
    # Default: Run as stdio for fastmcp dev command
    import sys
    if "--dev" in sys.argv:
        # For development with Inspector UI - let fastmcp dev handle it
        mcp.run()
    else:
        # For direct HTTP access
        mcp.run(transport="http", host="0.0.0.0", port=8008)