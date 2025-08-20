# Swagger API Documentation

This markdown file provides a concise reference for sharing Press API endpoints using Swagger (OpenAPI).

## How to Use

1. Review the complete list of available methods in [API_DOCS.md](API_DOCS.md).
2. Use the generated [SWAGGER_APIS.json](SWAGGER_APIS.json) file as a starting point for your Swagger/OpenAPI definition.
3. Select the endpoints you want to expose and refine details as needed.
4. Import the final OpenAPI file into [Swagger UI](https://swagger.io/tools/swagger-ui/) or any compatible tool to visualize and interact with the API.

## Example OpenAPI Snippet

```yaml
openapi: 3.0.0
info:
  title: Press API
  version: 1.0.0
paths:
  /api/method/press.api.account.get:
    get:
      summary: Get account details
      responses:
        '200':
          description: Successful response
```

Use the above pattern to document additional endpoints and share the generated OpenAPI file through Swagger.
