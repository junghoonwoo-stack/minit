import os

from minit.monitoring import ProcessMonitor


def test_process_monitor_reports_local_memory_and_cpu_fields():
    monitor = ProcessMonitor(os.getpid())
    sample = monitor.sample()

    assert sample["available"] is True
    assert isinstance(sample["rss_bytes"], int)
    assert sample["rss_bytes"] > 0
    assert "cpu_percent" in sample
    assert isinstance(sample["child_processes"], int)
