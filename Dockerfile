FROM python:3.12-slim
WORKDIR /app
COPY requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt
COPY app.py monitor.py ./
COPY static ./static
COPY .streamlit ./.streamlit
USER 10001:10001
ENV STREAMLIT_SERVER_ADDRESS=0.0.0.0 STREAMLIT_SERVER_PORT=8080
EXPOSE 8080
CMD ["streamlit", "run", "app.py", "--server.headless=true"]
