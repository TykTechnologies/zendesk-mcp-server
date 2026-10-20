import asyncio
import json
import logging
import os
from datetime import datetime
from typing import Any, Literal

from cachetools.func import ttl_cache
from dotenv import load_dotenv
from mcp.server import MCPServer

from zendesk_mcp_server.zendesk_client import ZendeskClient

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)
logger = logging.getLogger("zendesk-mcp-server")
logger.info("zendesk mcp server started")

load_dotenv()
zendesk_client = ZendeskClient(
    subdomain=os.getenv("ZENDESK_SUBDOMAIN"),
    email=os.getenv("ZENDESK_EMAIL"),
    token=os.getenv("ZENDESK_API_KEY")
)

server = MCPServer("zendesk-server", version="0.1.0")

TICKET_ANALYSIS_TEMPLATE = """
You are a helpful Zendesk support analyst. You've been asked to analyze ticket #{ticket_id}.

Please fetch the ticket info and comments to analyze it and provide:
1. A summary of the issue
2. The current status and timeline
3. Key points of interaction

Remember to be professional and focus on actionable insights.
"""

COMMENT_DRAFT_TEMPLATE = """
You are a helpful Zendesk support agent. You need to draft a response to ticket #{ticket_id}.

Please fetch the ticket info, comments and knowledge base to draft a professional and helpful response that:
1. Acknowledges the customer's concern
2. Addresses the specific issues raised
3. Provides clear next steps or ask for specific details need to proceed
4. Maintains a friendly and professional tone
5. Ask for confirmation before commenting on the ticket

The response should be formatted well and ready to be posted as a comment.
"""


@server.prompt(name="analyze-ticket", description="Analyze a Zendesk ticket and provide insights")
def analyze_ticket(ticket_id: str) -> str:
    return TICKET_ANALYSIS_TEMPLATE.format(ticket_id=ticket_id).strip()


@server.prompt(name="draft-ticket-response", description="Draft a professional response to a Zendesk ticket")
def draft_ticket_response(ticket_id: str) -> str:
    return COMMENT_DRAFT_TEMPLATE.format(ticket_id=ticket_id).strip()


@server.tool(name="get_ticket", description="Retrieve a Zendesk ticket by its ID")
def get_ticket(ticket_id: int) -> str:
    ticket = zendesk_client.get_ticket(ticket_id)
    return json.dumps(ticket)


@server.tool(name="get_organization", description="Retrieve a Zendesk organization by its ID. Returns org name, domain names, details, notes, tags, and other metadata.")
def get_organization(organization_id: int) -> str:
    org = zendesk_client.get_organization(organization_id)
    return json.dumps(org)


@server.tool(name="search_organizations", description="Find Zendesk organizations by name. Returns up to 10 matches, each with id and name only. Use the id with get_organization or the organization filter of search_tickets.")
def search_organizations(name: str) -> str:
    orgs = zendesk_client.search_organizations(name)
    return json.dumps(orgs)


@server.tool(name="update_organization", description="Update fields on a Zendesk organization (e.g., notes, tags, details, domain_names)")
def update_organization(
    organization_id: int,
    name: str | None = None,
    details: str | None = None,
    notes: str | None = None,
    domain_names: list[str] | None = None,
    tags: list[str] | None = None,
    group_id: int | None = None,
    shared_tickets: bool | None = None,
    shared_comments: bool | None = None,
    external_id: str | None = None,
) -> str:
    update_fields = {k: v for k, v in {
        "name": name, "details": details, "notes": notes,
        "domain_names": domain_names, "tags": tags, "group_id": group_id,
        "shared_tickets": shared_tickets, "shared_comments": shared_comments,
        "external_id": external_id,
    }.items() if v is not None}
    updated = zendesk_client.update_organization(organization_id=organization_id, **update_fields)
    return json.dumps({"message": "Organization updated successfully", "organization": updated}, indent=2)


@server.tool(name="create_ticket", description="Create a new Zendesk ticket")
def create_ticket(
    subject: str,
    description: str,
    requester_id: int | None = None,
    assignee_id: int | None = None,
    priority: str | None = None,
    type: str | None = None,
    tags: list[str] | None = None,
    custom_fields: list[dict] | None = None,
) -> str:
    created = zendesk_client.create_ticket(
        subject=subject,
        description=description,
        requester_id=requester_id,
        assignee_id=assignee_id,
        priority=priority,
        type=type,
        tags=tags,
        custom_fields=custom_fields,
    )
    return json.dumps({"message": "Ticket created successfully", "ticket": created}, indent=2)


@server.tool(name="search_tickets", description="Search Zendesk tickets with filters for status, priority, assignee, requester, commenter, dates, and more")
def search_tickets(
    query: str | None = None,
    status: Literal["new", "open", "pending", "hold", "solved", "closed"] | None = None,
    priority: Literal["low", "normal", "high", "urgent"] | None = None,
    assignee: int | None = None,
    requester: int | None = None,
    commenter: int | None = None,
    group: int | None = None,
    organization: int | None = None,
    tags: list[str] | None = None,
    created_after: str | None = None,
    created_before: str | None = None,
    updated_after: str | None = None,
    updated_before: str | None = None,
    sort_by: str = "created_at",
    sort_order: str = "desc",
    page: int = 1,
    per_page: int = 25,
) -> str:
    ca = datetime.fromisoformat(created_after.replace("Z", "+00:00")) if created_after else None
    cb = datetime.fromisoformat(created_before.replace("Z", "+00:00")) if created_before else None
    ua = datetime.fromisoformat(updated_after.replace("Z", "+00:00")) if updated_after else None
    ub = datetime.fromisoformat(updated_before.replace("Z", "+00:00")) if updated_before else None

    tickets = zendesk_client.search_tickets(
        query=query,
        status=status,
        priority=priority,
        assignee=assignee,
        requester=requester,
        commenter=commenter,
        group=group,
        organization=organization,
        tags=tags,
        created_after=ca,
        created_before=cb,
        updated_after=ua,
        updated_before=ub,
        sort_by=sort_by,
        sort_order=sort_order,
        page=page,
        per_page=per_page,
    )
    return json.dumps(tickets, indent=2)


@server.tool(name="get_ticket_comments", description="Retrieve all comments for a Zendesk ticket by its ID")
def get_ticket_comments(ticket_id: int) -> str:
    comments = zendesk_client.get_ticket_comments(ticket_id)
    return json.dumps(comments)


@server.tool(name="create_ticket_comment", description="Create a new comment on an existing Zendesk ticket")
def create_ticket_comment(ticket_id: int, comment: str, public: bool = True) -> str:
    result = zendesk_client.post_comment(
        ticket_id=ticket_id,
        comment=comment,
        public=public
    )
    return f"Comment created successfully: {result}"


@server.tool(name="update_ticket", description="Update fields on an existing Zendesk ticket (e.g., status, priority, assignee_id)")
def update_ticket(
    ticket_id: int,
    subject: str | None = None,
    status: str | None = None,
    priority: str | None = None,
    type: str | None = None,
    assignee_id: int | None = None,
    requester_id: int | None = None,
    tags: list[str] | None = None,
    custom_fields: list[dict] | None = None,
    due_at: str | None = None,
) -> str:
    update_fields = {k: v for k, v in {
        "subject": subject, "status": status, "priority": priority,
        "type": type, "assignee_id": assignee_id, "requester_id": requester_id,
        "tags": tags, "custom_fields": custom_fields, "due_at": due_at,
    }.items() if v is not None}
    updated = zendesk_client.update_ticket(ticket_id=ticket_id, **update_fields)
    return json.dumps({"message": "Ticket updated successfully", "ticket": updated}, indent=2)


@server.resource("zendesk://knowledge-base", name="Zendesk Knowledge Base", description="Access to Zendesk Help Center articles and sections", mime_type="application/json")
def knowledge_base() -> str:
    kb_data = get_cached_kb()
    return json.dumps({
        "knowledge_base": kb_data,
        "metadata": {
            "sections": len(kb_data),
            "total_articles": sum(len(section['articles']) for section in kb_data.values()),
        }
    }, indent=2)


@ttl_cache(ttl=3600)
def get_cached_kb():
    return zendesk_client.get_all_articles()


async def main():
    await server.run_stdio_async()


if __name__ == "__main__":
    asyncio.run(main())
