.PHONY: install backend frontend test reset

install:
	cd backend && pip install -r requirements.txt
	cd frontend && npm install

backend:
	cd backend && uvicorn app.main:app --reload --port 8000

frontend:
	cd frontend && npm run dev

test:
	cd backend && pytest -q

reset:          ## drop the demo database and reseed
	rm -f backend/creator_fit.db
	cd backend && python -m app.seed
