import logging
from simulation.grpc.server import serve

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(name)s %(message)s")
    serve().wait_for_termination()
