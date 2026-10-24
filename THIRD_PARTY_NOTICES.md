# Dependencies and sources

Project-specific robot XML, controller, text classifier, example sentences, UI, and recording scripts were authored for this assignment with AI coding assistance. No source code from the course samples was copied.

Runtime dependencies are installed separately with pip, not embedded in the source archive:

- MuJoCo: Apache-2.0; https://github.com/google-deepmind/mujoco
- NumPy: BSD-3-Clause; https://numpy.org/
- Pillow: HPND; https://python-pillow.org/
- ImageIO: BSD-2-Clause; https://github.com/imageio/imageio
- imageio-ffmpeg: BSD-2-Clause wrapper. The separately installed wheel includes FFmpeg; see its distribution's licenses and build information: https://github.com/imageio/imageio-ffmpeg
- Transitive dependencies and exact versions are listed in requirements-lock.txt. Their original licenses remain applicable.
- Optional PDF generator: ReportLab (BSD); https://www.reportlab.com/

Japanese text uses a font available on the user's operating system (Meiryo on tested Windows). The font files are not distributed with the project. PDFs may embed a subset for displaying the document.

Background reference supplied in the course: https://qiita.com/N622/items/9d89f77d85d9da0af29e (ROS 2/Gazebo connection concepts; not used as implementation code).

MuJoCo API reference: https://mujoco.readthedocs.io/en/stable/python.html

The software models a simplified classroom scenario, not a production vehicle parking or safety system.
