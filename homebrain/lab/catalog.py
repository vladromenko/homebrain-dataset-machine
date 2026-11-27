"""Generic demonstrations reuse native recipes; scientific decks stay with plugins."""
from .contracts import ProjectDescriptor, TaskCard, RobotCapability


RECIPES = {
    "so101-placement": ("so101", "Place a cube in the marked box", "so101_pick_place", ["top", "wrist"]),
    "tank-docking": ("tank", "Approach the marked docking zone", "tank_dock", ["front"]),
    "rosmaster-docking": ("rosmaster", "Dock with the arm stationary", "rosmaster_dock", ["front"]),
    "rosmaster-placement": ("rosmaster", "Place a cube with the base stationary", "rosmaster_pick_place", ["front"]),
}


def descriptor():
    return ProjectDescriptor(project_id="demonstrations", title="Robot demonstrations", version="1.0.0",
        protocol_revision="native-demonstrations-v1", modes=["development"], robot_ids=["so101", "tank", "rosmaster"],
        task_groups=[{"id": "development", "title": "Native human demonstrations"}],
        capabilities=["native_recording", "native_validation"]).model_dump()


def tasks():
    return [TaskCard(task_id=key, project_id="demonstrations", title=title,
        protocol_revision="native-demonstrations-v1", plan_revision="development-no-study-quota",
        robot_id=robot, dataset_intent="human_motor_demonstration", camera_roles=cameras,
        setup=["Clear the motion area and keep the native STOP reachable.",
               "Place the object and target inside every required view.",
               "Use the native leader arm or the selected keyboard/gamepad control."],
        control_profile=profile, source_group="development", split="unallocated",
        allowed_actions=["prepare_session"], outcome_requirements=["outcome", "assisted"],
        eligibility="native_checks_required").model_dump() for key, (robot, title, profile, cameras) in RECIPES.items()]


def capabilities(studio, explorer):
    preview = studio.get("preview", {}).get("cameras", {})
    cameras = [{"role": role, "stable_id": value.get("stream", {}).get("device"),
                "age_ms": value.get("last_frame_age_ms"), "connected": value.get("connected"),
                "owner": "Studio", "source": "native_shared", "stream": value.get("stream", {})}
               for role, value in preview.items()]
    profiles = explorer.get("profiles", {})
    return [RobotCapability(robot_id=robot, display_name=label, domain="physical", native_owner=owner,
        state="available" if available else "unavailable", inputs=inputs,
        operations=["prepare_session", "enable_control", "start_recording", "finish_recording", "stop"],
        cameras=cameras if robot == "so101" else [{"role": "front", "source": "native_agent", "freshness": "readback_required"}],
        sensors=[{"profile": key, "provenance": value} for key, value in profiles.items() if value["robot"] == robot],
        recorders=["native LeRobot"], unsupported=["calibrated shared world transform"],
        models=[{"provenance": "existing native MuJoCo; dynamics not hardware calibrated"}]).model_dump()
        for robot, label, owner, available, inputs in [
            ("so101", "SO101", "Studio", bool(studio), ["leader arm"]),
            ("tank", "Tank", "Explorer", bool(explorer), ["keyboard", "gamepad"]),
            ("rosmaster", "ROSMASTER", "Explorer", bool(explorer), ["keyboard", "gamepad", "leader mirror"])]]
