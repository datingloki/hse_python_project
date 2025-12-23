update:
	git pull
	docker compose up -d --build
	@echo "Изменения подтянулись в докер"