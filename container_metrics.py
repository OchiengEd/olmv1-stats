#!/usr/bin/env python3

from kubernetes import config, dynamic
from kubernetes.client import api_client as k8s_client
from kubernetes.dynamic.resource import ResourceField
from dataclasses import dataclass

from datetime import datetime
import pandas as pd
import time
import sys

# Interval between data collection in seconds
interval = 2
# Number of datapoints to collect
samples = 150

@dataclass
class KubeMetrics:
    """Keep track on the OLM v1 Kubernetes metrics"""
    name: str
    containers: list[ResourceField]
    
    def get_containers(self) -> list[ResourceField]:
        return self.containers

    def get_pod(self) -> str:
        return self.name

    def raw_data(self) -> list[str]:
        data: list[str] = []
        data.append(self.name)

        containers = sorted(self.containers, key=lambda container: container['name'], reverse=True)
        for container in containers:
            data.append(container.name)
            data.append(container.usage.cpu)
            data.append(container.usage.memory)

        return data


def get_olm_metrics() -> list[KubeMetrics]:
    client = dynamic.DynamicClient(k8s_client.ApiClient(configuration=config.load_kube_config()))
    metrics_api = client.resources.get(api_version='metrics.k8s.io/v1beta1', kind='PodMetrics')

    metrics: list[KubeMetrics] = []
    pods = [ podmetrics for podmetrics in metrics_api.get().items if podmetrics.metadata.namespace == 'olmv1-system' ]
    for pod in pods:
        if pod.metadata.name.startswith(("catalogd", "operator-controller"), 0):
            metrics.append(KubeMetrics(name=pod.metadata.name, containers=pod.containers))

    return metrics

def timestamp() -> str:
    return datetime.now().strftime("%Y%m%d-%H%M")

def main() -> None:
    metrics_filename = 'olm_v1_metrics-{}.csv'.format(timestamp())
    count = 0
    d : list[str] = []

    while True:
        metrics = get_olm_metrics()
        for metric in metrics:
            d.append(metric.raw_data())
        time.sleep(interval)
        count += 1
        if count >= samples:
            break

    df = pd.DataFrame(data=d, columns=["pod","c0","cpu0","mem0","c1","cpu1","mem1"])
    df.to_csv(metrics_filename)
    print('Metrics written to file {}'.format(metrics_filename))

if __name__ == '__main__':
    main()
