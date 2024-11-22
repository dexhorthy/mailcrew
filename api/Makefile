.PHONY: run
run:
	uv run -m app.main


.PHONY: test-email
test-email:
	curl -X POST http://localhost:8000/api/v1/webhook/email \
		-H "Content-Type: application/json" \
		--data-binary '{"from_address": "dexter@humanlayer.dev", "to_address": "agent@reply.humanlayer.dev", "subject": "send an invoice to joe", "body": "what products and prices are available?", "raw_email": "__raw email__", "message_id": "1234567890"}'
