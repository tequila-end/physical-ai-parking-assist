"""Differential-drive robot in MuJoCo. Motion is produced by wheel actuators."""

import math

import mujoco
import numpy as np

from parking_rules import DEMO_SLOTS


def scene_xml(slots=DEMO_SLOTS):
    bays = []
    colors = [(0.20, 0.48, 0.85), (0.10, 0.65, 0.52), (0.88, 0.53, 0.18)]
    for slot, color in zip(slots, colors):
        x, y = slot.destination_xy
        rgba = ' '.join(map(str, (*color, 1)))
        bays.append(f'<geom name="bay_{slot.name}" type="box" pos="{x} {y} 0.003" size=".72 1.05 .003" rgba="{rgba}" contype="0" conaffinity="0"/>')
        for edge in (-.76, .76):
            bays.append(f'<geom type="box" pos="{x + edge} {y} .008" size=".025 1.10 .008" rgba=".9 .94 .95 1" contype="0" conaffinity="0"/>')
        if slot.occupied:
            bays.append(f'<geom name="occupied_{slot.name}" type="box" pos="{x} {y} .27" size=".38 .66 .27" rgba=".42 .46 .52 1"/>')
            bays.append(f'<geom type="box" pos="{x} {y + .10} .62" size=".30 .35 .10" rgba=".16 .21 .27 1"/>')
    return '''<mujoco model="AI parking robot">
      <compiler angle="radian"/>
      <option timestep="0.004166666666666667" gravity="0 0 -9.81" integrator="implicitfast"/>
      <visual><global offwidth="960" offheight="600"/><quality shadowsize="2048"/><headlight ambient=".45 .45 .45" diffuse=".7 .7 .7"/></visual>
      <default><geom friction="1 .005 .0001" solref=".01 1"/><joint damping=".03" armature=".01"/></default>
      <asset><texture name="sky" type="skybox" builtin="gradient" rgb1=".80 .88 .95" rgb2=".98 .99 1" width="128" height="128"/>
      <material name="floor" rgba=".21 .26 .32 1"/></asset>
      <worldbody>
        <light pos="0 -3 7" dir="0 .3 -1" diffuse=".9 .9 .9"/>
        <geom name="floor" type="plane" size="10 10 .1" material="floor"/>
        <geom type="box" pos="1 3 .16" size="4 .07 .16" rgba=".42 .47 .54 1"/>
        <geom type="box" pos="1 -3 .01" size="4 .03 .01" rgba=".65 .72 .78 1" contype="0" conaffinity="0"/>
        ''' + '\n'.join(bays) + '''
        <body name="robot" pos="-2.4 -1.5 .23">
          <freejoint/>
          <geom name="chassis" type="box" size=".25 .18 .07" mass="3" rgba=".94 .96 .98 1"/>
          <geom type="box" pos=".12 0 .10" size=".09 .14 .035" mass=".15" rgba=".05 .68 .60 1"/>
          <geom type="box" pos="-.1 0 .12" size=".08 .13 .05" mass=".15" rgba=".12 .17 .24 1"/>
          <body name="left_wheel" pos="0 .22 -.10"><joint name="left" axis="0 1 0"/>
            <geom type="cylinder" size=".12 .035" euler="1.57079632679 0 0" mass=".2" rgba=".06 .08 .10 1"/>
          </body>
          <body name="right_wheel" pos="0 -.22 -.10"><joint name="right" axis="0 1 0"/>
            <geom type="cylinder" size=".12 .035" euler="1.57079632679 0 0" mass=".2" rgba=".06 .08 .10 1"/>
          </body>
          <geom name="caster_front" type="sphere" pos=".20 0 -.16" size=".055" mass=".05" friction=".001 .001 .0001" rgba=".18 .20 .22 1" priority="1"/>
          <geom name="caster_back" type="sphere" pos="-.20 0 -.16" size=".055" mass=".05" friction=".001 .001 .0001" rgba=".18 .20 .22 1" priority="1"/>
        </body>
      </worldbody>
      <actuator><velocity name="drive_left" joint="left" kv="3" ctrllimited="true" ctrlrange="-12 12" forcelimited="true" forcerange="-8 8"/>
      <velocity name="drive_right" joint="right" kv="3" ctrllimited="true" ctrlrange="-12 12" forcelimited="true" forcerange="-8 8"/></actuator>
    </mujoco>'''


def wrap_angle(angle):
    return (angle + math.pi) % (2 * math.pi) - math.pi


class ParkingSimulation:
    def __init__(self, decision, slots=DEMO_SLOTS):
        self.model = mujoco.MjModel.from_xml_string(scene_xml(slots))
        self.data = mujoco.MjData(self.model)
        self.robot_id = self.model.body('robot').id
        self.decision = decision
        self.renderer = None
        self.path = []
        self.stage = 0
        self.arrived = False
        self.failed = False
        self.collision = False
        self.max_position_jump = 0.0
        robot_bodies = {self.model.body(name).id for name in ('robot', 'left_wheel', 'right_wheel')}
        self.robot_geoms = {i for i in range(self.model.ngeom) if self.model.geom_bodyid[i] in robot_bodies}
        self.obstacles = {i for i in range(self.model.ngeom) if self.model.geom_bodyid[i] == 0
                          and self.model.geom_contype[i] != 0 and i != self.model.geom('floor').id}
        self.camera = mujoco.MjvCamera()
        self.camera.lookat[:] = (1.0, .1, 0)
        self.camera.distance = 9.6
        self.camera.azimuth = 100
        self.camera.elevation = -57
        mujoco.mj_forward(self.model, self.data)
        # Let contacts settle before issuing wheel commands.
        for _ in range(120):
            mujoco.mj_step(self.model, self.data)
        self.start_time = self.data.time
        self.start_xy = self.xy.copy()
        if decision['status'] == 'ready':
            x, y = decision['destination_xy']
            self.path = [(x, -1.5), (x, y)]

    @property
    def xy(self):
        return self.data.xpos[self.robot_id, :2].copy()

    @property
    def yaw(self):
        matrix = self.data.xmat[self.robot_id].reshape(3, 3)
        return math.atan2(matrix[1, 0], matrix[0, 0])

    @property
    def elapsed(self):
        return self.data.time - self.start_time

    @property
    def status(self):
        if self.failed:
            return 'timeout'
        if self.arrived:
            return 'arrived'
        if not self.path:
            return self.decision['status']
        return 'driving'

    def step(self, steps=8):
        for _ in range(steps):
            before = self.xy
            v, omega = 0.0, 0.0
            if self.path and not self.arrived and not self.failed:
                target = self.path[self.stage]
                dx, dy = target[0] - before[0], target[1] - before[1]
                distance = math.hypot(dx, dy)
                if distance < .10:
                    if self.stage + 1 < len(self.path):
                        self.stage += 1
                    else:
                        heading_error = wrap_angle(math.pi / 2 - self.yaw)
                        omega = max(-1.6, min(1.6, 3.0 * heading_error))
                        if abs(heading_error) < .06 and np.linalg.norm(self.data.qvel[:2]) < .07:
                            self.arrived = True
                else:
                    error = wrap_angle(math.atan2(dy, dx) - self.yaw)
                    omega = max(-1.8, min(1.8, 3 * error))
                    if abs(error) < .4:
                        v = min(.72, .9 * distance) * max(0, math.cos(error))
                if self.elapsed > 32:
                    self.failed = True
                    v, omega = 0.0, 0.0
            self.data.ctrl[:] = ((v - omega * .22) / .12, (v + omega * .22) / .12)
            mujoco.mj_step(self.model, self.data)
            self.max_position_jump = max(self.max_position_jump, float(np.linalg.norm(self.xy - before)))
            for contact in self.data.contact[:self.data.ncon]:
                if (contact.geom1 in self.obstacles and contact.geom2 in self.robot_geoms) or (contact.geom2 in self.obstacles and contact.geom1 in self.robot_geoms):
                    self.collision = True

    def render(self):
        if self.renderer is None:
            self.renderer = mujoco.Renderer(self.model, height=500, width=850)
        self.renderer.update_scene(self.data, camera=self.camera)
        return self.renderer.render()

    def result(self):
        result = {'status': self.status, 'elapsed_s': round(self.elapsed, 2),
                  'position_xy': self.xy.round(4).tolist(), 'collision': self.collision,
                  'max_step_displacement_m': round(self.max_position_jump, 6)}
        if self.path:
            result['position_error_m'] = round(float(np.linalg.norm(self.xy - np.array(self.path[-1]))), 4)
        else:
            result['drift_m'] = round(float(np.linalg.norm(self.xy - self.start_xy)), 6)
        return result

    def close(self):
        if self.renderer is not None:
            self.renderer.close()
