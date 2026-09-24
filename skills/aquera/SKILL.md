---
name: aquera
description: Operate Aquera shrimp farm ponds, logs, and harvests.
version: 1.0.0
author: Tony + Hermes Agent
license: MIT
platforms: [linux, macos, windows]
metadata:
  hermes:
    tags: [aquera, shrimp-farming, aquaculture, openapi, farm-management]
    category: operations
    config:
      aquera_base_url:
        description: Base URL of the Aquera API
        default: https://aquera.id/api/v1
      aquera_api_secret:
        description: Secret token for Aquera API authentication
        secret: true
      aquera_cid:
        description: Default tenant organization CID
---

# Aquera Shrimp Farming Skill

Manage and operate the Aquera smart shrimp farming platform via its OpenAPI 3.1.0 REST API. This skill allows Hermes to read, record, update, and manage shrimp farm data including ponds, farming cycles, stocking, daily feeding logs, water and growth samplings, harvests, and sales invoices.

## When to Use

Use this skill when:
- The user asks to view or inspect farm metrics, ponds, cycles, or operational summaries.
- The user requests recording daily pond operations: feed distribution (`feed-log`), water quality/growth measurements (`sampling`), or seedling stocking (`stocking`).
- The user asks to create or adjust master farm data: farm sites (`farm-sites`), ponds (`ponds`), feed brands (`feed-brands`), or cycles (`cycles`).
- The user requests recording harvest batches (`harvest`) or generating buyer invoices (`invoice`).

Do not use this skill for unrelated farm analytics or direct database access without the API layer.

## Prerequisites

- Aquera REST API specification: `./openapi.json`.
- Environment variables or configuration keys:
  - `AQUERA_BASE_URL`: Base API URL (e.g., `https://aquera.id/api/v1`).
  - `AQUERA_API_SECRET`: API Secret token (sent via `Authorization: Bearer <SECRET>` or `x-api-key`).
  - `AQUERA_CID`: Target organization tenant ID (sent via `x-cid: <CID>`).
- Network access from Hermes to the Aquera API host.

## How to Run

1. Verify that `AQUERA_API_SECRET` and `AQUERA_CID` are configured in your environment or Hermes config.
2. Read the API schema from `./openapi.json` to inspect parameter formats and endpoint paths.
3. Execute HTTP requests using `terminal` (via `curl` or Python script) or through the native Hermes OpenAPI toolset dispatcher.

## Quick Reference

| Action | Method | Path | Required Headers | Key Parameters |
|---|---|---|---|---|
| Health Check | `GET` | `/health` | (none) | None |
| Dashboard KPI | `GET` | `/summary` | `Authorization`, `x-cid` | None |
| List Ponds | `GET` | `/ponds` | `Authorization`, `x-cid` | None |
| Create Pond | `POST` | `/ponds` | `Authorization`, `x-cid` | `farm_site_id`, `name`, `area_m2` |
| Update Pond | `PUT` | `/ponds` | `Authorization`, `x-cid` | `id`, `name` or `area_m2` |
| Delete Pond | `DELETE` | `/ponds?id={id}` | `Authorization`, `x-cid` | `id` (query) |
| Log Feed | `POST` | `/feed-log` | `Authorization`, `x-cid` | `cycle_id`, `pond_id`, `qty_kg`, `fed_at` |
| Log Sampling | `POST` | `/sampling` | `Authorization`, `x-cid` | `cycle_id`, `pond_id`, `sampled_at`, `abw_g` |
| Record Harvest | `POST` | `/harvest` | `Authorization`, `x-cid` | `pond_id`, `cycle_id`, `harvest_type`, `details` |
| Create Invoice | `POST` | `/invoice` | `Authorization`, `x-cid` | `buyer_name`, `invoice_date`, `items` |

## Procedure

### 1. Context Resolution & ID Lookup
Most update (`PUT`) and delete (`DELETE`) operations require an explicit entity UUID (`id`). When a user mentions an entity by human name (e.g. *"Kolam A1"* or *"Grobest No. 1"*):
- First call the corresponding `GET` endpoint (e.g., `GET /api/v1/ponds`).
- Search the returned array for the matching name to extract its UUID `id`.
- Proceed with the mutation using the discovered UUID.

### 2. Executing Mutations (POST, PUT, DELETE)
- Always pass both `Authorization: Bearer <SECRET>` and `x-cid: <CID>`.
- For `POST` and `PUT`, format the body as JSON matching the schema in `openapi.json`.
- For `DELETE`, supply the UUID in the query string (e.g., `DELETE /api/v1/ponds?id=<UUID>`).

### 3. Error Handling
- **401 Unauthorized:** Secret key is missing or invalid. Check `AQUERA_API_SECRET`.
- **403 Forbidden:** Organization CID is missing or inactive. Check `x-cid` value.
- **400 Bad Request:** Missing required fields or schema validation failed. Re-check `openapi.json`.
- **500 Server Error:** Database connectivity issue. Call `GET /api/v1/health` to diagnose.

## Pitfalls

- **Missing `x-cid` Header:** Aquera is strictly multi-tenant. Requests without `x-cid` return 401/403.
- **Direct Deletions without Confirmation:** Always confirm with the user before executing destructive `DELETE` actions.
- **Harvest Batching:** Harvest details expect an array of size and quantity entries: `[{ size: 50, qty_kg: 500, price_per_kg: 73000 }]`.
- **Date Format:** All date fields must follow ISO 8601 `YYYY-MM-DD` or full ISO timestamp `YYYY-MM-DDTHH:mm:ssZ`.

## Verification

1. Run `GET /api/v1/health` and verify `status: "healthy"`.
2. Run `GET /api/v1/organization` with `x-cid` and verify your farm organization profile loads.
3. Test a read operation like `GET /api/v1/ponds` or `GET /api/v1/summary`.