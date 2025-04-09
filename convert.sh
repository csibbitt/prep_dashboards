#!/bin/sh
if [ ! -d telemetry-operator ]; then git clone https://github.com/openstack-k8s-operators/telemetry-operator.git; fi
cd dashboards || exit
if [ ! -f dcgm-exporter-dashboard.json ]; then wget https://raw.githubusercontent.com/NVIDIA/dcgm-exporter/refs/heads/main/grafana/dcgm-exporter-dashboard.json; fi
if [ ! -f AMDSmiExporter_GPU_GrafanaDashboard.json ]; then wget https://raw.githubusercontent.com/amd/amd_smi_exporter/refs/heads/master/grafana/AMDSmiExporter_GPU_GrafanaDashboard.json; fi
if [ ! -f grafana-purefa-flasharray-overview.json ]; then wget https://raw.githubusercontent.com/PureStorage-OpenConnect/pure-fa-openmetrics-exporter/refs/heads/master/extra/grafana/grafana-purefa-flasharray-overview.json; fi
if [ ! -f junos_dashboard.json ]; then wget -O junos_dashboard.json https://raw.githubusercontent.com/czerwonk/junos_exporter/refs/heads/main/example/dashboard/grafana_dashboard.json; fi
cd ..
./prep_dashboards.py
podman run --name perses -d --rm --replace -p 127.0.0.1:8080:8080 -v ./out:/tmp/out:Z -v ./migrated:/tmp/migrated:Z persesdev/perses
alias percli="podman exec perses percli --percliconfig /tmp/perses_config.json"
sleep 5
percli login http://localhost:8080
for f in out/*.json; do percli migrate -f "/tmp/${f}" --online > "migrated/$(basename "${f}")"; done
for f in out/*.json; do OE=$(grep -c expr "${f}"); MQ=$(grep -c query "migrated/$(basename "${f}")"); echo "{$f} - Original: ${OE} Migrated: ${MQ}"; done
echo '{"kind":"GlobalDatasource","metadata":{"name":"prometheus"},"spec":{"default":true,"plugin":{"kind":"PrometheusDatasource","spec":{"directUrl":"http://localhost:9090"}}}}' > migrated/datasource.json
echo '{"kind": "Project","metadata": {"name": "Imported"}}' > migrated/project.json
percli apply -f /tmp/migrated/project.json
for f in migrated/*.json; do percli apply -p Imported -f "/tmp/${f}"; done