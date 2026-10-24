"""Shared Japanese presentation for the local app and generated video."""

from functools import lru_cache
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw, ImageFont

from parking_rules import DEMO_SLOTS


BG = '#edf2f6'
INK = '#192d40'
MUTED = '#576d80'
TEAL = '#008c7c'
COLORS = ['#347dd7', '#1aa887', '#df882e']


@lru_cache(maxsize=30)
def font(size, bold=False):
    candidates = [Path('C:/Windows/Fonts/meiryob.ttc' if bold else 'C:/Windows/Fonts/meiryo.ttc'),
                  Path('/usr/share/fonts/opentype/noto/NotoSansCJK-Regular.ttc')]
    for candidate in candidates:
        if candidate.exists():
            return ImageFont.truetype(str(candidate), size)
    return ImageFont.load_default(size=size)


def wrapped(draw, text, x, y, width, size=20, fill=INK, spacing=9, bold=False):
    current = ''
    for char in text:
        if char == '\n' or (current and draw.textlength(current + char, font=font(size, bold)) > width):
            draw.text((x, y), current, font=font(size, bold), fill=fill)
            y += size + spacing
            current = '' if char == '\n' else char
        else:
            current += char
    if current:
        draw.text((x, y), current, font=font(size, bold), fill=fill)
        y += size + spacing
    return y


def heading(draw, tag='LOCAL AI / MuJoCo'):
    draw.text((28, 17), 'AI PARKING ASSIST', font=font(31, True), fill=INK)
    draw.text((29, 62), '要望を分類し、条件に合う駐車区画へ移動するロボット', font=font(19), fill=MUTED)
    draw.rounded_rectangle((989, 27, 1252, 65), radius=10, fill='#dceae9')
    draw.text((1005, 34), tag, font=font(17, True), fill=TEAL)


def frame(sim, scenario, inference, decision, slots=DEMO_SLOTS, phase=None):
    canvas = Image.new('RGB', (1280, 720), BG)
    draw = ImageDraw.Draw(canvas)
    heading(draw)
    draw.text((28, 101), scenario['title'], font=font(23, True), fill=INK)
    canvas.paste(Image.fromarray(sim.render()), (28, 146))
    draw.rounded_rectangle((895, 100, 1252, 646), radius=16, fill='white')
    x = 916
    y = 118
    draw.text((x, y), '入力された要望', font=font(17, True), fill=MUTED)
    y = wrapped(draw, '「' + scenario['text'] + '」', x, y + 33, 312, size=21, bold=True)
    y += 13
    draw.text((x, y), f"車高：{scenario['height']:.2f} m", font=font(23, True), fill=INK)
    y += 49
    draw.line((x, y, 1230, y), fill='#e1e9ee', width=2)
    draw.text((x, y + 19), 'AIの分類結果', font=font(17, True), fill=MUTED)
    y = wrapped(draw, inference['reason'], x, y + 50, 312, size=23, fill=TEAL, bold=True)
    y += 18
    status = phase or sim.status
    labels = {'planning': '条件を確認', 'driving': '走行中', 'arrived': '到着・停止',
              'blocked': '発進しません', 'clarify': '要望の確認待ち', 'timeout': '走行タイムアウト', 'invalid': '入力を確認'}
    status_color = '#b36511' if status in ('blocked','clarify','invalid','timeout') else TEAL
    draw.rounded_rectangle((x, y, 1230, y + 48), radius=8, fill=status_color)
    label = labels.get(status, status)
    if decision.get('slot'):
        label += '  /  区画' + decision['slot']
    draw.text((x + 14, y + 9), label, font=font(22, True), fill='white')
    y = wrapped(draw, decision['reason'], x, y + 64, 307, size=18)
    if scenario.get('explanation'):
        wrapped(draw, scenario['explanation'], x, max(y + 12, 512), 307, size=15, spacing=6, fill=MUTED)
    draw.text((x, 605), 'AI：文字特徴を学習した分類器', font=font(15), fill=MUTED)
    for index, slot in enumerate(slots):
        bx = 28 + index * 287
        draw.rounded_rectangle((bx, 654, bx + 275, 708), radius=8, fill='white')
        draw.rounded_rectangle((bx, 654, bx + 7, 708), radius=3, fill=COLORS[index])
        draw.text((bx + 17, 661), f'{slot.name}  高さ {slot.max_height_m:.2f}mまで', font=font(18, True), fill=INK)
        draw.text((bx + 17, 686), '満車' if slot.occupied else '空車', font=font(13), fill=MUTED)
    draw.text((918, 667), '物理演算・車輪駆動 / 等速', font=font(17), fill=MUTED)
    draw.text((918, 691), f'シミュレーション経過 {sim.elapsed:05.1f} 秒', font=font(13), fill=MUTED)
    return np.asarray(canvas)


def title_card(final=False, metrics=None):
    image = Image.new('RGB', (1280,720), BG)
    d = ImageDraw.Draw(image)
    heading(d)
    d.rounded_rectangle((45, 135, 1235, 645), radius=24, fill='white')
    if not final:
        d.text((78, 164), '言葉の要望を、ロボットの動作へ。', font=font(39, True), fill=INK)
        wrapped(d, '小さな文章分類AIと、車高・満車を確認する制御を組み合わせます。', 80, 230, 1090, 23)
        items = [('01', 'AIが分類', '入口近く / 場所の指定なし'), ('02', '条件を照合', '車高制限・区画の空き状態'), ('03', '台車が実行', '車輪を回して移動・停止')]
        for i, (number, title, body) in enumerate(items):
            x = 80 + i * 385
            d.rounded_rectangle((x, 315, x + 350, 495), radius=16, fill='#eef4f7')
            d.text((x + 23, 332), number, font=font(28, True), fill=TEAL)
            d.text((x + 23, 382), title, font=font(28, True), fill=INK)
            wrapped(d, body, x + 23, 438, 307, 18)
        wrapped(d, 'Windowsローカル実行 / 外部AI APIなし / MuJoCoによる物理シミュレーション\n映像は等速。各ケースは初期状態へ戻して開始します。', 80, 542, 1090, 20)
    else:
        d.text((78, 165), '結果と、この作品の範囲', font=font(37, True), fill=INK)
        lines = ['✓  同じ車高でも、AIが読み取った要望で行き先が変化',
                 '✓  入口近くの希望よりも、車高制限を優先',
                 '✓  対応区画が満車のときは移動命令を出さない']
        for i, line in enumerate(lines):
            d.text((80, 250 + 57*i), line, font=font(25, True), fill=TEAL)
        correct = metrics['correct'] if metrics else 12
        total = metrics['evaluation_examples'] if metrics else 12
        wrapped(d, f'AI：自作例文48件で学習。別の例文{total}件中{correct}件を正しく分類。\n少数の例文での結果であり、自由な日本語全般への精度保証ではありません。', 80, 449, 1090, 21)
        wrapped(d, '固定通路・既知の区画情報・台車1台に限定。実車の駐車や画像認識は対象外です。', 80, 554, 1090, 20, fill=MUTED)
    return np.asarray(image)
