from locust import HttpUser, between, task


class HiringOSUser(HttpUser):
    wait_time = between(0.5, 2.0)

    @task(5)
    def health(self):
        self.client.get('/healthz')

    @task(5)
    def ready(self):
        self.client.get('/readyz')

