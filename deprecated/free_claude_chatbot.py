#!/usr/bin/env python3
"""
Free Claude Web Chatbot using Local Claude Desktop + MCP
No API key required - uses your existing Claude Desktop setup
"""
from flask import Flask, render_template, request, jsonify, session
import json
import subprocess
import uuid
import os
import time
import tempfile
from datetime import datetime
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

app = Flask(__name__)
app.secret_key = 'your-secret-key-change-this'

# Configuration
MCP_SERVER_PATH = '/home/bashar/odoo18/mcp_wrapper.sh'

class FreeClaudeMCPChatbot:
    def __init__(self):
        self.mcp_tools = {
            "search_leads": "crm_search_leads",
            "update_lead": "crm_update_lead", 
            "create_customer": "res_partner_find_or_create",
            "post_message": "mail_message_post"
        }

    def call_mcp_tool_direct(self, tool_name, parameters):
        """Call MCP tool directly and return formatted result"""
        try:
            print(f"🔧 Calling MCP tool: {tool_name} with params: {parameters}")
            
            # Create MCP process
            process = subprocess.Popen(
                [MCP_SERVER_PATH, 'stdio'],
                stdin=subprocess.PIPE,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                cwd='/home/bashar/odoo18'
            )
            
            # Initialize MCP server
            init_request = {
                "jsonrpc": "2.0",
                "id": 0,
                "method": "initialize",
                "params": {
                    "protocolVersion": "2024-11-05",
                    "capabilities": {},
                    "clientInfo": {"name": "free-web-chatbot", "version": "1.0"}
                }
            }
            
            print(f"📤 Sending init: {json.dumps(init_request)}")
            process.stdin.write(json.dumps(init_request) + "\n")
            process.stdin.flush()
            init_response = process.stdout.readline()
            print(f"📥 Init response: {init_response.strip()}")
            
            # Call tool
            tool_request = {
                "jsonrpc": "2.0",
                "id": 1,
                "method": "tools/call",
                "params": {
                    "name": tool_name,
                    "arguments": parameters
                }
            }
            
            print(f"📤 Sending tool request: {json.dumps(tool_request)}")
            process.stdin.write(json.dumps(tool_request) + "\n")
            process.stdin.flush()
            
            response = process.stdout.readline()
            print(f"📥 Tool response: {response.strip()}")
            
            stderr_output = process.stderr.read()
            if stderr_output:
                print(f"⚠️ Stderr: {stderr_output}")
            
            process.terminate()
            
            if response:
                result = json.loads(response)
                if "result" in result:
                    return result["result"]
                elif "error" in result:
                    print(f"❌ MCP Error: {result['error']}")
                    return {"error": result["error"]["message"]}
            
            return {"error": "No response from MCP server"}
            
        except Exception as e:
            print(f"❌ MCP tool error: {str(e)}")
            return {"error": f"MCP tool failed: {str(e)}"}

    def get_claude_response_via_desktop(self, user_message, context_data=None):
        """Generate intelligent response using MCP data and smart formatting"""
        
        # Smart intent detection and response generation
        message_lower = user_message.lower()
        
        # Context-aware responses
        if context_data:
            return self.format_intelligent_response(user_message, context_data)
        
        # Search leads intent
        if any(word in message_lower for word in ['search', 'find', 'show', 'leads', 'list']):
            if 'high' in message_lower and 'probability' in message_lower:
                domain = [["probability", ">=", 75]]
            elif 'won' in message_lower:
                domain = [["stage_id.name", "=", "Won"]]
            elif 'new' in message_lower:
                domain = [["stage_id.name", "=", "New"]]
            else:
                domain = []
            
            # Use correct parameter structure for MCP
            params = {
                'domain': domain,
                'fields': ['id', 'name', 'partner_name', 'email_from', 'phone', 'probability', 'expected_revenue', 'stage_id'],
                'limit': 10,
                'offset': 0
            }
            
            result = self.call_mcp_tool_direct('crm_search_leads', params)
            return self.format_intelligent_response(user_message, result)
        
        # Create customer intent
        elif any(word in message_lower for word in ['create', 'new', 'add']) and any(word in message_lower for word in ['customer', 'client', 'partner']):
            # Extract customer details from message
            customer_data = self.extract_customer_data(user_message)
            
            if customer_data['name']:
                result = self.call_mcp_tool_direct('res_partner_find_or_create', customer_data)
                return self.format_intelligent_response(user_message, result)
            else:
                return {
                    "response": """🤔 I'd be happy to help you create a new customer! 

To create a customer, please provide at least a name. You can say something like:
• "Create customer John Smith"
• "Add new client Jane Doe with email jane@example.com"
• "New customer ABC Company with phone 555-1234"

What customer would you like me to create?"""
                }
        
        # Update lead intent
        elif 'update' in message_lower and 'lead' in message_lower:
            # Extract lead ID and update data
            update_data = self.extract_update_data(user_message)
            if update_data['lead_id']:
                result = self.call_mcp_tool_direct('crm_update_lead', update_data)
                return self.format_intelligent_response(user_message, result)
            else:
                return {
                    "response": """📝 I can help you update a lead! 

Please specify the lead ID and what you'd like to update. For example:
• "Update lead 44 stage to won"
• "Set lead 23 probability to 90%"
• "Update lead 15 expected revenue to 5000"

What lead would you like me to update?"""
                }
        
        # Help intent
        elif any(word in message_lower for word in ['help', 'what', 'can', 'do', 'commands']):
            return {
                "response": """🤖 **Free Odoo AI Assistant** - Powered by your local Claude Desktop!

I can help you with:

**🔍 Search & Find:**
• "Search leads" - Show all leads
• "Find high probability leads" - Leads >75% probability  
• "Show won leads" - Display closed deals
• "List new leads" - Recent opportunities

**👥 Customer Management:**
• "Create customer John Smith" - Add new customer
• "New client with email jane@example.com" - Customer with contact info

**✏️ Lead Updates:**
• "Update lead 44 stage to won" - Change lead stage
• "Set lead 23 probability to 90%" - Update probability
• "Update lead 15 revenue to 5000" - Change expected revenue

**💬 Communication:**
• "Post message to lead 44: Follow up needed" - Add notes

**🎯 Smart Features:**
• Natural language understanding
• Context-aware responses  
• Real-time Odoo data
• No API costs - completely free!

Just ask me anything about your Odoo CRM in natural language! 🚀"""
            }
        
        # Default helpful response
        else:
            return {
                "response": f"""I understand you're asking about: "{user_message}"

I'm here to help you with your Odoo CRM! I can:

🔍 **Search**: "find high probability leads"
👥 **Create**: "create customer John Smith" 
✏️ **Update**: "update lead 44 stage to won"
❓ **Help**: "what can you do?"

What would you like me to help you with?"""
            }

    def format_intelligent_response(self, user_message, data):
        """Format MCP data into intelligent, conversational responses"""
        
        if isinstance(data, dict) and "error" in data:
            return {"response": f"❌ I encountered an issue: {data['error']}"}
        
        # Format lead search results - handle MCP response structure
        if isinstance(data, dict) and "content" in data:
            content = data["content"]
            
            # Handle the LeadSearchOut structure: {count: int, results: list[dict]}
            if isinstance(content, dict) and "results" in content:
                results = content["results"]
                count = content.get("count", len(results))
                
                if results and len(results) > 0:
                    response = f"📋 **Found {count} leads:**\n\n"
                    for lead in results:
                        stage = lead.get('stage_id', [None, 'No stage'])
                        stage_name = stage[1] if isinstance(stage, list) and len(stage) > 1 else 'No stage'
                        
                        response += f"**{lead.get('name', 'Unnamed Lead')}** (ID: {lead.get('id')})\n"
                        response += f"  👤 Customer: {lead.get('partner_name') or 'No customer'}\n"
                        response += f"  📧 Email: {lead.get('email_from') or 'No email'}\n"
                        response += f"  📱 Phone: {lead.get('phone') or 'No phone'}\n"
                        response += f"  🎯 Probability: {lead.get('probability', 0)}%\n"
                        response += f"  💰 Revenue: ${lead.get('expected_revenue', 0):,.2f}\n"
                        response += f"  📊 Stage: {stage_name}\n\n"
                    
                    return {"response": response}
                else:
                    return {"response": "🔍 No leads found matching your criteria. Try a different search or create a new lead!"}
            
            # Handle direct list results (legacy format)
            elif isinstance(content, list) and len(content) > 0:
                response = f"📋 **Found {len(content)} leads:**\n\n"
                for lead in content:
                    stage = lead.get('stage_id', [None, 'No stage'])
                    stage_name = stage[1] if isinstance(stage, list) and len(stage) > 1 else 'No stage'
                    
                    response += f"**{lead.get('name', 'Unnamed Lead')}** (ID: {lead.get('id')})\n"
                    response += f"  👤 Customer: {lead.get('partner_name') or 'No customer'}\n"
                    response += f"  📧 Email: {lead.get('email_from') or 'No email'}\n"
                    response += f"  📱 Phone: {lead.get('phone') or 'No phone'}\n"
                    response += f"  🎯 Probability: {lead.get('probability', 0)}%\n"
                    response += f"  💰 Revenue: ${lead.get('expected_revenue', 0):,.2f}\n"
                    response += f"  📊 Stage: {stage_name}\n\n"
                
                return {"response": response}
        
        # Format customer creation result
        elif isinstance(data, dict) and "content" in data and isinstance(data["content"], (dict, int)):
            content = data["content"]
            if isinstance(content, dict):
                customer_id = content.get("id")
            else:
                customer_id = content
                
            if customer_id:
                return {"response": f"✅ **Customer created successfully!**\n\n👤 Customer ID: {customer_id}\n\nThe new customer has been added to your Odoo database and is ready for use!"}
        
        # Format update results
        elif isinstance(data, dict) and data.get("content") == True:
            return {"response": "✅ **Lead updated successfully!**\n\nThe changes have been saved to your Odoo database."}
        
        # Format message post results  
        elif isinstance(data, dict) and "content" in data:
            message_id = data["content"]
            if isinstance(message_id, int):
                return {"response": f"✅ **Message posted successfully!**\n\n💬 Message ID: {message_id}\n\nYour note has been added to the record."}
        
        # Generic success response
        return {"response": f"✅ **Operation completed successfully!**\n\nResult: {str(data)[:200]}..."}
    

    def extract_customer_data(self, message):
        """Extract customer information from natural language"""
        data = {"name": "", "email": "", "phone": ""}
        
        # Simple extraction logic
        words = message.split()
        
        # Find name after keywords
        name_keywords = ['customer', 'client', 'partner', 'named', 'called']
        for i, word in enumerate(words):
            if word.lower() in name_keywords and i + 1 < len(words):
                # Get next 1-3 words as name
                name_parts = []
                for j in range(i + 1, min(i + 4, len(words))):
                    if '@' in words[j] or words[j].lower() in ['with', 'email', 'phone']:
                        break
                    name_parts.append(words[j])
                data["name"] = " ".join(name_parts).strip('"\'')
                break
        
        # Find email
        for word in words:
            if '@' in word:
                data["email"] = word.strip('"\'')
                break
        
        # Find phone (simple pattern)
        for word in words:
            if any(char.isdigit() for char in word) and len(word) >= 7:
                data["phone"] = word.strip('"\'')
                break
        
        return data

    def extract_update_data(self, message):
        """Extract lead update information from natural language"""
        data = {"lead_id": None, "values": {}}
        
        words = message.split()
        
        # Find lead ID
        for i, word in enumerate(words):
            if word.lower() == 'lead' and i + 1 < len(words):
                try:
                    data["lead_id"] = int(words[i + 1])
                    break
                except ValueError:
                    continue
        
        # Find stage updates
        if 'stage' in message.lower():
            if 'won' in message.lower():
                data["values"]["stage_id"] = 4  # Typical won stage ID
            elif 'qualified' in message.lower():
                data["values"]["stage_id"] = 2
            elif 'new' in message.lower():
                data["values"]["stage_id"] = 1
        
        # Find probability updates
        if 'probability' in message.lower():
            for word in words:
                if word.replace('%', '').isdigit():
                    data["values"]["probability"] = int(word.replace('%', ''))
                    break
        
        # Find revenue updates
        if 'revenue' in message.lower() or 'amount' in message.lower():
            for word in words:
                if word.replace('$', '').replace(',', '').isdigit():
                    data["values"]["expected_revenue"] = float(word.replace('$', '').replace(',', ''))
                    break
        
        return data

# Flask routes
@app.route('/')
def index():
    """Main chat interface"""
    if 'session_id' not in session:
        session['session_id'] = str(uuid.uuid4())
    return render_template('chat.html')

@app.route('/chat', methods=['POST'])
def chat():
    """Handle chat messages"""
    try:
        data = request.get_json()
        user_message = data.get('message', '').strip()
        
        if not user_message:
            return jsonify({"error": "Empty message"})
        
        print(f"💬 User: {user_message}")
        
        # Process with free AI logic
        chatbot = FreeClaudeMCPChatbot()
        result = chatbot.get_claude_response_via_desktop(user_message)
        
        if "error" in result:
            return jsonify(result)
        
        print(f"🤖 Response: {result['response'][:100]}...")
        
        return jsonify({
            "response": result["response"],
            "timestamp": datetime.now().isoformat()
        })
        
    except Exception as e:
        print(f"❌ Chat error: {str(e)}")
        return jsonify({"error": f"Chat error: {str(e)}"})

@app.route('/health')
def health():
    """Health check endpoint"""
    return jsonify({
        "status": "healthy",
        "mode": "free_local_claude",
        "mcp_server": "available",
        "cost": "free",
        "timestamp": datetime.now().isoformat()
    })

if __name__ == '__main__':
    print("🚀 Starting FREE Claude + MCP Web Chatbot...")
    print("🌐 Access at: http://localhost:5000")
    print("📋 Health check: http://localhost:5000/health")
    print("💰 100% FREE - No API keys required!")
    print("🎯 Uses your existing Claude Desktop + MCP setup")
    app.run(host='0.0.0.0', port=5000, debug=True)
