import threading
import time


def worker(name: str) -> None:
    for step in range(3):
        print(f"{name}: step {step}")
        time.sleep(0.5)


if __name__ == "__main__":
    begin = time.perf_counter()

    t1 = threading.Thread(target=worker, args=("A",), daemon=False)
    t2 = threading.Thread(target=worker, args=("B",), daemon=False)
    t1.start()
    t2.start()
    t1.join()
    t2.join()

    print(f"elapsed: {time.perf_counter() - begin:.2f}s")
