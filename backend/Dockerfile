FROM ubuntu:latest
LABEL authors="Samukelo.Mfusi"

ENTRYPOINT ["top", "-b"]

FROM python:3.11-slim

WORKDIR /app

<<<<<<< HEAD
COPY ../requirements.txt .
=======
COPY requirements.txt .
>>>>>>> b46545bf3 (Add build and dist folders)
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

EXPOSE 8000

CMD ["python", "run_system.py"]