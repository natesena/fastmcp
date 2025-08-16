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
import subprocess
from datetime import datetime
from pathlib import Path
from typing import Optional, Dict, List, Any
from dotenv import load_dotenv

from fastmcp import FastMCP

# Load environment variables
load_dotenv()

# Get the database path from environment variable
IMESSAGES_DB_PATH = os.getenv("IMESSAGES_DB_PATH", str(Path.home() / "Library/Messages/chat.db"))

mcp = FastMCP("iMessage Server")

# Global contact cache
CONTACT_CACHE = None
CONTACT_PHONE_LOOKUP = None


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


def normalize_phone(phone: str) -> str:
    """Normalize a phone number to just digits for comparison"""
    # Keep only digits
    digits = ''.join(filter(str.isdigit, phone))
    
    # Handle common US phone formats
    if len(digits) == 10:  # Missing country code
        digits = '1' + digits
    elif len(digits) == 11 and digits[0] == '1':  # Has US country code
        pass  # Already normalized
    
    return digits


def load_contact_cache():
    """Load all contacts into memory for fast lookups"""
    global CONTACT_CACHE, CONTACT_PHONE_LOOKUP
    
    if CONTACT_CACHE is not None:
        return  # Already loaded
    
    print("Loading contact cache...")
    
    # Get all contacts with a reasonable timeout
    script = '''
tell application "Contacts"
    set contactList to {}
    set allPeople to people
    
    repeat with currentPerson in allPeople
        try
            set personName to name of currentPerson
            set personPhones to {}
            
            -- Get phone numbers
            try
                set phonesList to phones of currentPerson
                repeat with phoneItem in phonesList
                    try
                        set phoneValue to value of phoneItem
                        if phoneValue is not "" then
                            set personPhones to personPhones & {phoneValue}
                        end if
                    on error
                    end try
                end repeat
            on error
            end try
            
            -- Format output (simplified - just name and phones)
            if (count of personPhones) > 0 then
                set phoneString to ""
                repeat with i from 1 to count of personPhones
                    set phoneString to phoneString & item i of personPhones
                    if i < count of personPhones then
                        set phoneString to phoneString & ";"
                    end if
                end repeat
                
                set contactInfo to personName & "|" & phoneString
                set contactList to contactList & {contactInfo}
            end if
        on error
        end try
    end repeat
    
    -- Return as delimited string
    set AppleScript's text item delimiters to "\\n"
    set resultString to contactList as string
    set AppleScript's text item delimiters to ""
    
    return resultString
end tell
'''
    
    try:
        result = run_applescript(script, timeout=60)  # Allow 60 seconds to load all contacts
        
        CONTACT_CACHE = {}
        CONTACT_PHONE_LOOKUP = {}
        
        if result:
            lines = result.strip().split('\n')
            for line in lines:
                if '|' in line:
                    parts = line.split('|')
                    if len(parts) >= 2:
                        name = parts[0].strip()
                        phones = [p.strip() for p in parts[1].split(';') if p.strip()]
                        
                        CONTACT_CACHE[name] = phones
                        
                        # Build reverse lookup with normalized phones
                        for phone in phones:
                            normalized = normalize_phone(phone)
                            if normalized:
                                CONTACT_PHONE_LOOKUP[normalized] = name
                                
                                # Also store without country code for flexibility
                                if normalized.startswith('1') and len(normalized) == 11:
                                    CONTACT_PHONE_LOOKUP[normalized[1:]] = name
        
        print(f"Loaded {len(CONTACT_CACHE)} contacts with {len(CONTACT_PHONE_LOOKUP)} phone numbers")
        
    except Exception as e:
        print(f"Failed to load contact cache: {e}")
        CONTACT_CACHE = {}
        CONTACT_PHONE_LOOKUP = {}


def run_applescript(script: str, timeout: int = 30) -> str:
    """Run an AppleScript and return the result"""
    try:
        result = subprocess.run(
            ['osascript', '-e', script],
            capture_output=True,
            text=True,
            timeout=timeout
        )
        if result.returncode != 0:
            if "Not authorized to send Apple events" in result.stderr:
                raise Exception(
                    "Permission denied: Please grant Contacts access.\n"
                    "1. Open System Settings > Privacy & Security > Automation\n"
                    "2. Find your terminal app (Terminal/iTerm/VS Code) in the list\n"
                    "3. Enable the checkbox next to 'Contacts'\n"
                    "4. Restart your terminal and try again"
                )
            raise Exception(f"AppleScript error: {result.stderr}")
        return result.stdout.strip()
    except subprocess.TimeoutExpired:
        raise Exception(f"AppleScript execution timed out after {timeout} seconds")
    except Exception as e:
        if "Permission denied" in str(e):
            raise e
        raise Exception(f"Failed to run AppleScript: {str(e)}")


@mcp.tool
def get_contacts_count() -> Dict[str, Any]:
    """Get the total number of contacts in your Contacts app"""
    script = '''
tell application "Contacts"
    set totalCount to count of people
    return totalCount
end tell
'''
    
    try:
        result = run_applescript(script, timeout=5)  # Quick operation
        count = int(result) if result else 0
        return {
            "total_contacts": count,
            "message": f"You have {count} contacts in your Contacts app"
        }
    except Exception as e:
        return {"error": str(e)}


@mcp.tool
def check_contacts_permission() -> Dict[str, Any]:
    """Check if the app has permission to access Contacts and provide setup instructions"""
    try:
        # Simple test to check Contacts access
        test_script = 'tell application "Contacts" to return name'
        run_applescript(test_script)
        return {
            "has_permission": True,
            "message": "Contacts access is granted. You can use all contact-related tools."
        }
    except Exception as e:
        error_msg = str(e)
        if "Permission denied" in error_msg or "Not authorized" in error_msg:
            return {
                "has_permission": False,
                "message": error_msg,
                "instructions": [
                    "To enable Contacts access:",
                    "1. Open System Settings (System Preferences on older macOS)",
                    "2. Go to Privacy & Security > Automation",
                    "3. Find your terminal application:",
                    "   - Terminal.app",
                    "   - iTerm.app", 
                    "   - Visual Studio Code",
                    "   - Or whatever terminal you're using",
                    "4. Click the checkbox next to 'Contacts' to enable access",
                    "5. You may need to restart your terminal application",
                    "",
                    "Alternative method:",
                    "1. Open System Settings > Privacy & Security > Contacts",
                    "2. Click the '+' button",
                    "3. Add your terminal application",
                    "4. Restart the terminal"
                ]
            }
        else:
            return {
                "has_permission": False,
                "message": f"Unable to access Contacts: {error_msg}"
            }


@mcp.tool
def get_all_contacts(limit: int = 50, offset: int = 0) -> Dict[str, Any]:
    """Get contacts from macOS Contacts app with pagination support
    
    Args:
        limit: Maximum number of contacts to return (default 50)
        offset: Number of contacts to skip (for pagination, default 0)
    
    Returns:
        Dictionary with contacts, total count, and pagination info
    """
    script = f'''
tell application "Contacts"
    set contactList to {{}}
    set allPeople to people
    set totalCount to count of allPeople
    set startIndex to {offset + 1}
    set endIndex to {offset + limit}
    
    if startIndex > totalCount then
        return "EMPTY|0|" & totalCount
    end if
    
    if endIndex > totalCount then
        set endIndex to totalCount
    end if
    
    repeat with i from startIndex to endIndex
        set currentPerson to item i of allPeople
        try
            set personName to name of currentPerson
            set personPhones to {{}}
            set personEmails to {{}}
            
            -- Get phone numbers
            try
                set phonesList to phones of currentPerson
                repeat with phoneItem in phonesList
                    try
                        set phoneValue to value of phoneItem
                        set phoneLabel to label of phoneItem
                        if phoneValue is not "" then
                            set personPhones to personPhones & {{phoneLabel & ": " & phoneValue}}
                        end if
                    on error
                        -- Skip problematic phone entries
                    end try
                end repeat
            on error
                -- No phones
            end try
            
            -- Get email addresses
            try
                set emailsList to emails of currentPerson
                repeat with emailItem in emailsList
                    try
                        set emailValue to value of emailItem
                        set emailLabel to label of emailItem
                        if emailValue is not "" then
                            set personEmails to personEmails & {{emailLabel & ": " & emailValue}}
                        end if
                    on error
                        -- Skip problematic email entries
                    end try
                end repeat
            on error
                -- No emails
            end try
            
            -- Format output
            set contactInfo to personName & "|"
            
            -- Add phones
            repeat with i from 1 to count of personPhones
                set contactInfo to contactInfo & item i of personPhones
                if i < count of personPhones then
                    set contactInfo to contactInfo & ";"
                end if
            end repeat
            
            set contactInfo to contactInfo & "|"
            
            -- Add emails
            repeat with i from 1 to count of personEmails
                set contactInfo to contactInfo & item i of personEmails
                if i < count of personEmails then
                    set contactInfo to contactInfo & ";"
                end if
            end repeat
            
            set contactList to contactList & {{contactInfo}}
        on error
            -- Skip problematic contacts
        end try
    end repeat
    
    -- Return as delimited string with count
    set AppleScript's text item delimiters to "\\n"
    set resultString to contactList as string
    set AppleScript's text item delimiters to ""
    
    return "DATA|" & (endIndex - startIndex + 1) & "|" & totalCount & "\\n" & resultString
end tell
'''
    
    try:
        result = run_applescript(script)
        
        if result.startswith("EMPTY"):
            parts = result.split("|")
            total = int(parts[2]) if len(parts) > 2 else 0
            return {
                "contacts": {},
                "pagination": {
                    "offset": offset,
                    "limit": limit,
                    "total": total,
                    "returned": 0,
                    "has_more": False
                }
            }
        
        lines = result.strip().split('\n')
        metadata_line = lines[0] if lines else ""
        contact_lines = lines[1:] if len(lines) > 1 else []
        
        # Parse metadata
        total_count = 0
        returned_count = 0
        if metadata_line.startswith("DATA|"):
            meta_parts = metadata_line.split("|")
            if len(meta_parts) >= 3:
                returned_count = int(meta_parts[1])
                total_count = int(meta_parts[2])
        
        contacts = {}
        for line in contact_lines:
            if '|' in line:
                parts = line.split('|')
                if len(parts) >= 2:
                    name = parts[0].strip()
                    phones = []
                    emails = []
                    
                    if len(parts) > 1 and parts[1]:
                        phones = [p.strip() for p in parts[1].split(';') if p.strip()]
                    
                    if len(parts) > 2 and parts[2]:
                        emails = [e.strip() for e in parts[2].split(';') if e.strip()]
                    
                    contacts[name] = {
                        "phones": phones,
                        "emails": emails
                    }
        
        return {
            "contacts": contacts,
            "pagination": {
                "offset": offset,
                "limit": limit,
                "total": total_count,
                "returned": len(contacts),
                "has_more": (offset + limit) < total_count
            }
        }
    except Exception as e:
        return {"error": str(e)}


@mcp.tool
def find_contact_by_name(name: str, limit: int = 10) -> Dict[str, Any]:
    """Find contacts by name and return their phone numbers and emails
    
    Args:
        name: The name to search for (partial matching supported)
        limit: Maximum number of results to return (default 10)
    
    Returns:
        Dictionary with matching contacts and search metadata
    """
    if not name or name.strip() == "":
        return {"error": "Name parameter is required"}
    
    search_name = name.strip().replace('"', '\\"')  # Escape quotes
    
    # Optimized AppleScript that uses 'whose' clause for faster searching
    script = f'''
on run
    tell application "Contacts"
        set matchedContacts to {{}}
        set searchText to "{search_name}"
        
        -- Use 'whose' clause for faster searching
        try
            set matchingPeople to (people whose name contains searchText)
        on error
            -- If no exact matches, try broader search
            set matchingPeople to {{}}
        end try
        
        -- If no matches with contains, try more lenient search
        if (count of matchingPeople) = 0 then
            set allPeople to people
            set maxSearch to 100
            if (count of allPeople) < maxSearch then
                set maxSearch to count of allPeople
            end if
            
            repeat with i from 1 to maxSearch
                try
                    set currentPerson to item i of allPeople
                    set personName to name of currentPerson
                    
                    ignoring case
                        if personName contains searchText or searchText contains personName then
                            set matchingPeople to matchingPeople & {{currentPerson}}
                        end if
                    end ignoring
                on error
                end try
            end repeat
        end if
        
        -- Limit results
        set resultLimit to {limit}
        if (count of matchingPeople) > resultLimit then
            set matchingPeople to items 1 thru resultLimit of matchingPeople
        end if
        
        -- Process matched contacts
        repeat with currentPerson in matchingPeople
            try
                set personName to name of currentPerson
                set personPhones to {{}}
                set personEmails to {{}}
                
                -- Get phone numbers
                try
                    set phonesList to phones of currentPerson
                    repeat with phoneItem in phonesList
                        try
                            set phoneValue to value of phoneItem
                            set phoneLabel to label of phoneItem
                            if phoneValue is not "" then
                                set personPhones to personPhones & {{phoneLabel & ": " & phoneValue}}
                            end if
                        on error
                        end try
                    end repeat
                on error
                end try
                
                -- Get email addresses
                try
                    set emailsList to emails of currentPerson
                    repeat with emailItem in emailsList
                        try
                            set emailValue to value of emailItem
                            set emailLabel to label of emailItem
                            if emailValue is not "" then
                                set personEmails to personEmails & {{emailLabel & ": " & emailValue}}
                            end if
                        on error
                        end try
                    end repeat
                on error
                end try
                
                -- Format output
                set contactInfo to personName & "|"
                
                -- Add phones
                repeat with i from 1 to count of personPhones
                    set contactInfo to contactInfo & item i of personPhones
                    if i < count of personPhones then
                        set contactInfo to contactInfo & ";"
                    end if
                end repeat
                
                set contactInfo to contactInfo & "|"
                
                -- Add emails
                repeat with i from 1 to count of personEmails
                    set contactInfo to contactInfo & item i of personEmails
                    if i < count of personEmails then
                        set contactInfo to contactInfo & ";"
                    end if
                end repeat
                
                set matchedContacts to matchedContacts & {{contactInfo}}
            on error
            end try
        end repeat
        
        -- Return as delimited string
        set AppleScript's text item delimiters to "\\n"
        set resultString to matchedContacts as string
        set AppleScript's text item delimiters to ""
        
        return resultString
    end tell
end run
'''
    
    try:
        result = run_applescript(script)
        matches = []
        
        if result:
            lines = result.strip().split('\n')
            for line in lines:
                if '|' in line:
                    parts = line.split('|')
                    if len(parts) >= 2:
                        contact_name = parts[0].strip()
                        phones = []
                        emails = []
                        
                        if len(parts) > 1 and parts[1]:
                            phones = [p.strip() for p in parts[1].split(';') if p.strip()]
                        
                        if len(parts) > 2 and parts[2]:
                            emails = [e.strip() for e in parts[2].split(';') if e.strip()]
                        
                        matches.append({
                            "name": contact_name,
                            "phones": phones,
                            "emails": emails
                        })
        
        if matches:
            return {"matches": matches, "count": len(matches)}
        else:
            return {"message": f"No contacts found matching '{name}'", "matches": []}
            
    except Exception as e:
        return {"error": str(e)}


# Removed find_contact_by_phone - it was timing out with large contact lists


# Removed match_phone_to_contact - depends on find_contact_by_phone which was removed


# Removed get_messages_with_contact_names - depends on match_phone_to_contact which was removed


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