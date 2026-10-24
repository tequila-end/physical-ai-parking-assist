"""Optional report generator. Requires reportlab; not needed to run the robot."""

import argparse
import json
from pathlib import Path

from reportlab.lib import colors
from reportlab.lib.enums import TA_LEFT
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.units import mm
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, Image, PageBreak


ROOT = Path(__file__).resolve().parent
INK = colors.HexColor('#192d40')
TEAL = colors.HexColor('#008c7c')


def build(account):
    if not account or any(c in account for c in '<>:"/\\|?*'):
        raise ValueError('Use a valid account identifier for the filename')
    pdfmetrics.registerFont(TTFont('JP', 'C:/Windows/Fonts/meiryo.ttc', subfontIndex=0))
    pdfmetrics.registerFont(TTFont('JPBold', 'C:/Windows/Fonts/meiryob.ttc', subfontIndex=0))
    body = ParagraphStyle('body', fontName='JP', fontSize=9.3, leading=15.1, textColor=INK, wordWrap='CJK', spaceAfter=7)
    small = ParagraphStyle('small', parent=body, fontSize=8, leading=12, spaceAfter=4)
    heading = ParagraphStyle('heading', parent=body, fontName='JPBold', fontSize=12.3, leading=19, textColor=TEAL, spaceBefore=10, spaceAfter=6)
    title = ParagraphStyle('title', parent=body, fontName='JPBold', fontSize=19, leading=29, spaceAfter=8)
    eval_data = json.loads((ROOT/'artifacts'/'ai_evaluation.json').read_text(encoding='utf-8'))
    run = json.loads((ROOT/'artifacts'/'run_results.json').read_text(encoding='utf-8'))
    if not run['all_passed']:
        raise RuntimeError('Only generate the report after successful scenario validation')
    output = ROOT/'artifacts'/f'説明資料_PAI最終課題_{account}.pdf'
    doc = SimpleDocTemplate(str(output), pagesize=(210*mm,297*mm), rightMargin=16*mm,leftMargin=16*mm,
                            topMargin=17*mm,bottomMargin=16*mm, title='自然言語の要望に応じて駐車区画へ移動するロボット', author='')
    story = []
    def p(text, style=body):
        return Paragraph(text,style)
    def h(text):
        story.append(p(text,heading))
    story.extend([p('AI PARKING ASSIST',small),
                  p('自然言語の要望に応じて<br/>駐車区画へ移動するロボット',title),
                  p(f'Physical AI 応用1 最終課題　|　OmniCampus：{account}　|　2026年10月',small)])
    h('1. 背景・目的')
    story.append(p('駐車場では、利用者の「入口の近くがよい」といった希望と、車高制限・空車状態などの設備条件を両立する必要がある。本課題では、要望を読み取る小さなAIと、条件を厳密に確認する制御処理を分離し、条件に合う区画へ台車が移動する一連のタスクを実装した。'))
    h('2. タスクとシステム構成')
    story.append(p('区画3つ、差動二輪の台車1台、固定通路で構成する。台車は仮想車両の代理として走行し、入力された車高は区画選択の条件に使う。実車の積み下ろしやバック駐車は行わない。'))
    steps = [[p('<b>入力</b><br/>要望文＋車高',small),p('<b>AI</b><br/>要望を2分類',small),p('<b>判断ロジック</b><br/>車高・空車を照合',small),p('<b>ロボット制御</b><br/>車輪駆動で移動',small)]]
    diagram = Table(steps,colWidths=[126]*4)
    diagram.setStyle(TableStyle([('BACKGROUND',(0,0),(-1,-1),colors.HexColor('#edf4f6')),('BOX',(0,0),(-1,-1),.5,colors.HexColor('#c7d9e1')),('INNERGRID',(0,0),(-1,-1),.5,colors.white),('VALIGN',(0,0),(-1,-1),'TOP'),('LEFTPADDING',(0,0),(-1,-1),10),('TOPPADDING',(0,0),(-1,-1),9),('BOTTOMPADDING',(0,0),(-1,-1),7)]))
    story.extend([diagram,Spacer(1,9),p('Windows上のPythonとMuJoCoで完結する。ROS、Docker、外部AI APIは使用しない。画像認識を行わず、区画の空き状態と位置は既知の設定値として与える。',small)])
    story.append(Image(str(ROOT/'artifacts'/'scenario_1.png'),width=504,height=283.5))
    story.append(p('図1　要望の入力、AIの分類結果、区画選択、台車の到着を同一画面に表示。',small))
    story.append(p('区画A：高さ1.55mまで・空車　／　B：2.10mまで・空車　／　C：2.30mまで・満車。<br/>各ケースは同じ初期状態から開始する。',small))
    story.append(PageBreak())
    h('3. AIと制御の実装・工夫')
    story.append(p('<b>AI：</b>文字1個・2個の並びを特徴とする多項ナイーブベイズ分類器を実装した。自作の日本語例文48件（入口近く24件、指定なし24件）から文字特徴の出現頻度を学習し、新しい文を分類する。モデルはPC内で短時間に学習・推論し、学習済み大規模モデルの取得は不要。未知の文字特徴が多い文や低スコアの文は確認待ちにする。'))
    story.append(p('<b>区画選択：</b>車高制限を満たす空車区画だけを候補にする。「入口近く」なら近い候補を選び、「指定なし」なら近い区画を希望者のために残す運用ルールで遠い候補を選ぶ。適合区画が満車なら移動先を発行しない。AIの分類結果から車高や満車の制約を変更することはできない。'))
    story.append(p('<b>走行：</b>MuJoCoの車輪速度アクチュエータを用いる。シミュレータから台車の位置・向きを取得し、固定経由点に対する位置誤差と角度誤差から左右輪の速度を計算する。目標付近では減速し、目標から0.10m以内・所定の向きで停止する。移動中に台車の座標を直接書き換えていない。'))
    h('4. 結果')
    rows = [[p('ケース',small),p('AIの分類／条件',small),p('結果',small)]]
    details = [('入口近くを希望','入口近く・車高1.50m','Aへ到着'),('同じ車高で要望変更','指定なし・車高1.50m','Bへ到着'),('車高の制約を優先','入口近く・車高2.00m','Bへ到着'),('対応区画が満車','入口近く・車高2.20m','発進せず理由表示')]
    for row in details:
        rows.append([p(cell,small) for cell in row])
    table = Table(rows,colWidths=[160,185,159])
    table.setStyle(TableStyle([('BACKGROUND',(0,0),(-1,0),colors.HexColor('#dceeea')),('ROWBACKGROUNDS',(0,1),(-1,-1),[colors.whitesmoke,colors.white]),('LINEBELOW',(0,0),(-1,0),.7,TEAL),('VALIGN',(0,0),(-1,-1),'TOP'),('TOPPADDING',(0,0),(-1,-1),5),('BOTTOMPADDING',(0,0),(-1,-1),5)]))
    story.append(table)
    story.append(Spacer(1,7))
    max_error=max(item['motion'].get('position_error_m',0) for item in run['scenarios'])
    story.append(p(f'4ケースすべてで想定した結果を確認した。走行3ケースの到着判定時の最大位置誤差は{max_error:.3f}mで、静的障害物との接触は検出されなかった。別に用意した評価例文は{eval_data["evaluation_examples"]}件中{eval_data["correct"]}件が正解。入力検証など9件の自動テストも成功した。提出動画は約{run["video_seconds"]:.1f}秒、シミュレーション時間に対して等速である。'))
    h('5. 課題と今後の改善')
    story.append(p('評価は少数の自作例文と固定配置に限られる。分類スコアは正解確率を保証せず、複雑な否定・複数要望・対象外の文章を誤分類し得る。台車は車高ごとに形状を変更しておらず、車高は論理上の制約としてのみ扱う。満車時も物理演算上の微小な姿勢安定化は生じる。今後は例文の拡充、未知入力の判定改善、区画情報の実測、障害物回避を検討する。'))
    h('6. 使用技術・参考資料')
    story.append(p('Python 3.11.9 / MuJoCo 3.3.7 / NumPy 2.2.6 / Pillow 11.3.0 / ImageIO 2.37.0。<br/>モデル形状・文章分類器・制御・UIは本課題用に作成（AIコーディング支援を使用）。講義サンプルのコードの丸写しは行っていない。依存ライブラリは元のライセンスに従い、コードのTHIRD_PARTY_NOTICES.mdに記載した。',small))
    story.append(p('MuJoCo Python公式資料：<link href="https://mujoco.readthedocs.io/en/stable/python.html" color="#008c7c">https://mujoco.readthedocs.io/en/stable/python.html</link><br/>課題提示の参考例（考え方の参考）：<link href="https://qiita.com/N622/items/9d89f77d85d9da0af29e" color="#008c7c">https://qiita.com/N622/items/9d89f77d85d9da0af29e</link>',small))
    def footer(canvas,doc):
        canvas.setStrokeColor(colors.HexColor('#d3dfe6'))
        canvas.line(16*mm,13*mm,194*mm,13*mm)
        canvas.setFont('JP',8)
        canvas.setFillColor(colors.HexColor('#576d80'))
        canvas.drawString(16*mm,8.6*mm,'Physical AI 応用1 / AI PARKING ASSIST')
        canvas.drawRightString(194*mm,8.6*mm,str(doc.page))
    doc.build(story,onFirstPage=footer,onLaterPages=footer)
    return output


if __name__ == '__main__':
    parser=argparse.ArgumentParser()
    parser.add_argument('--account',required=True)
    args=parser.parse_args()
    print(build(args.account))
