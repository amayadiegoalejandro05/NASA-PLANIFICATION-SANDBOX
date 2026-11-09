"""Executable synthetic request; no network, NumPy, UI or ROS."""
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'prototypes/mission_planner'))
from demo_stage03 import example_request
from mission_api import plan_mission

if __name__ == '__main__':
    print(plan_mission(example_request('rover')).to_json())
