FROM python:3.12-slim
WORKDIR /app
COPY simulation/requirements.txt simulation/requirements.txt
RUN pip install --no-cache-dir -r simulation/requirements.txt
COPY simulation simulation
# generate protobuf stubs into the simulation.grpc package
RUN python -m grpc_tools.protoc -I. --python_out=. --grpc_python_out=. simulation/grpc/sim.proto
RUN python -m unittest discover -s simulation/tests -t . 
EXPOSE 50051
CMD ["python", "-m", "simulation.main"]
