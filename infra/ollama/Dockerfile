# Ollama with Llama 3.3 8B Q4_K_M pre-pulled.
# Model pull happens at first start via entrypoint.sh (download cached in volume).

FROM ollama/ollama:latest

COPY entrypoint.sh /entrypoint.sh
RUN chmod +x /entrypoint.sh

ENTRYPOINT ["/entrypoint.sh"]
CMD ["serve"]
