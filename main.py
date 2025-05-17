import uvicorn

if __name__ == "__main__":
    uvicorn.run("studying_assistant.deployment.app:app", host="127.0.0.1", port=8000, reload=True)
