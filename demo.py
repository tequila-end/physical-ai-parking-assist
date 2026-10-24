"""Run repeatable scenarios, validate motion, and optionally record a submission MP4."""

import argparse
import json
from pathlib import Path

import imageio.v2 as imageio
from PIL import Image

from intent_ai import IntentClassifier
from parking_rules import DEMO_SLOTS
from presentation import frame, title_card
from simulation import ParkingSimulation
from tasks import SCENARIOS, prepare_task


ROOT = Path(__file__).resolve().parent
FPS = 30


def run(record=False, output_dir=None):
    folder = Path(output_dir or ROOT / 'artifacts')
    folder.mkdir(parents=True, exist_ok=True)
    classifier = IntentClassifier()
    evaluation = classifier.evaluate()
    (folder / 'ai_evaluation.json').write_text(json.dumps(evaluation, ensure_ascii=False, indent=2), encoding='utf-8')
    results = []
    video = None
    frame_count = 0
    if record:
        video = imageio.get_writer(str(folder / 'parking_demo.mp4'), fps=FPS, codec='libx264',
                                   macro_block_size=1, quality=None, ffmpeg_params=['-crf','21','-preset','veryfast'])

    def write(pixels, count=1):
        nonlocal frame_count
        if video is not None:
            for _ in range(count):
                video.append_data(pixels)
                frame_count += 1

    try:
        if record:
            write(title_card(), 7 * FPS)
        for index, scenario in enumerate(SCENARIOS):
            inference, decision = prepare_task(scenario['text'], scenario['height'], classifier=classifier)
            sim = ParkingSimulation(decision)
            try:
                if record:
                    write(frame(sim, scenario, inference, decision, phase='planning'), 4 * FPS)
                horizon = 8 if not sim.path else 34
                while sim.elapsed < horizon and not sim.arrived and not sim.failed:
                    sim.step()
                    if record:
                        pixels = frame(sim, scenario, inference, decision)
                        write(pixels)
                result = sim.result()
                if sim.path:
                    # Verify stopping for a full second after declaring arrival.
                    before = sim.xy
                    for _ in range(FPS):
                        sim.step()
                        if record:
                            write(frame(sim, scenario, inference, decision))
                    import numpy as np
                    result['post_stop_drift_m'] = round(float(np.linalg.norm(sim.xy - before)), 6)
                expected = scenario['expected']
                passed = (result['status'] == 'blocked' and result.get('drift_m', 1) < .03) if expected == 'blocked' else (
                    decision.get('slot') == expected and result['status'] == 'arrived'
                    and result.get('position_error_m', 1) < .12 and result.get('post_stop_drift_m', 1) < .03
                    and not result['collision'])
                entry = {'scenario': scenario, 'inference': inference, 'decision': decision, 'motion': result, 'passed': passed}
                results.append(entry)
                print(json.dumps(entry, ensure_ascii=False), flush=True)
                if record:
                    pixels = frame(sim, scenario, inference, decision)
                    Image.fromarray(pixels).save(folder / f'scenario_{index + 1}.png')
                    write(pixels, 4 * FPS)
                if not passed:
                    raise RuntimeError(f'Scenario {index + 1} failed; inspect results before using the video')
            finally:
                sim.close()
        if record:
            write(title_card(final=True, metrics=evaluation), 9 * FPS)
    finally:
        if video is not None:
            video.close()
        report = {'scenarios': results, 'all_passed': len(results)==len(SCENARIOS) and all(r['passed'] for r in results),
                  'video_frames': frame_count, 'video_fps': FPS, 'video_seconds': round(frame_count/FPS, 3)}
        result_name = 'run_results.json' if record else 'validation_results.json'
        (folder / result_name).write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding='utf-8')
    if record and not 60 <= frame_count/FPS <= 180:
        raise RuntimeError('Video duration must be between 1 and 3 minutes')
    return report


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--record', action='store_true')
    parser.add_argument('--output-dir')
    args = parser.parse_args()
    result = run(args.record, args.output_dir)
    print('PASS' if result['all_passed'] else 'FAIL', flush=True)
