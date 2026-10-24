"""One-window local demo. Uses the same inference and physical simulation as video generation."""

import tkinter as tk
from dataclasses import replace
from tkinter import messagebox, ttk

from PIL import Image, ImageTk

from intent_ai import IntentClassifier
from parking_rules import DEMO_SLOTS
from presentation import frame, title_card
from simulation import ParkingSimulation
from tasks import SCENARIOS, prepare_task


class ParkingApp:
    def __init__(self):
        self.root = tk.Tk()
        self.root.title('AI Parking Assist - ローカル駐車場ロボット')
        self.root.geometry('1180x820')
        self.root.configure(bg='#edf2f6')
        self.classifier = IntentClassifier()
        self.sim = None
        self.scheduled = None
        self.auto_index = None
        self.text = tk.StringVar(value=SCENARIOS[0]['text'])
        self.height = tk.StringVar(value='1.50')
        self.occupied = [tk.BooleanVar(value=s.occupied) for s in DEMO_SLOTS]
        self.controls = ttk.Frame(self.root, padding=12)
        self.controls.pack(fill='x')
        ttk.Label(self.controls, text='要望').grid(row=0, column=0, padx=5)
        ttk.Entry(self.controls, textvariable=self.text, width=48).grid(row=0,column=1,padx=5)
        ttk.Label(self.controls, text='車高(m)').grid(row=0,column=2,padx=5)
        ttk.Combobox(self.controls, textvariable=self.height, values=['1.50','2.00','2.20'],width=7).grid(row=0,column=3,padx=5)
        ttk.Button(self.controls, text='実行', command=self.manual).grid(row=0,column=4,padx=8)
        ttk.Button(self.controls, text='4ケース自動デモ', command=self.auto).grid(row=0,column=5,padx=8)
        ttk.Button(self.controls, text='停止', command=self.stop).grid(row=0,column=6,padx=8)
        presets = ttk.Frame(self.root, padding=(12,0,12,8))
        presets.pack(fill='x')
        ttk.Button(presets,text='入口近くの例文',command=lambda:self.text.set(SCENARIOS[0]['text'])).pack(side='left',padx=5)
        ttk.Button(presets,text='指定なしの例文',command=lambda:self.text.set(SCENARIOS[1]['text'])).pack(side='left',padx=5)
        for slot, value in zip(DEMO_SLOTS,self.occupied):
            ttk.Checkbutton(presets,text=f'区画{slot.name}を満車にする',variable=value).pack(side='left',padx=14)
        self.view = tk.Label(self.root, bg='#edf2f6')
        self.view.pack(fill='both',expand=True)
        self.note = ttk.Label(self.root, text='「実行」するたびに初期位置へ戻ります。車高は台車に搭載する仮想車両の条件です。', padding=8)
        self.note.pack(fill='x')
        self.display(title_card())
        self.root.protocol('WM_DELETE_WINDOW', self.close)

    def display(self, pixels):
        image = Image.fromarray(pixels).resize((1152,648), Image.Resampling.LANCZOS)
        self.photo = ImageTk.PhotoImage(image)
        self.view.configure(image=self.photo)

    def stop(self):
        self.auto_index = None
        if self.scheduled is not None:
            self.root.after_cancel(self.scheduled)
            self.scheduled = None
        if self.sim is not None:
            self.sim.close()
            self.sim = None
        self.note.configure(text='停止しました。再開するには「実行」を押してください。')

    def manual(self):
        self.stop()
        try:
            height = float(self.height.get())
        except ValueError:
            messagebox.showerror('車高を確認', '車高は1.50のような数値で入力してください。')
            return
        self.slots = tuple(replace(s, occupied=v.get()) for s,v in zip(DEMO_SLOTS,self.occupied))
        self.begin({'title':'自由入力で実行', 'text':self.text.get(), 'height':height}, self.slots)

    def auto(self):
        self.stop()
        self.auto_index = 0
        for slot,value in zip(DEMO_SLOTS,self.occupied):
            value.set(slot.occupied)
        self.begin(SCENARIOS[0], DEMO_SLOTS)

    def begin(self, scenario, slots):
        self.scenario = scenario
        self.slots = slots
        self.text.set(scenario['text'])
        self.height.set(f"{scenario['height']:.2f}")
        self.inference,self.decision = prepare_task(scenario['text'],scenario['height'],slots,self.classifier)
        try:
            self.sim = ParkingSimulation(self.decision,slots)
            self.note.configure(text='表示速度はPCの描画性能に依存します。録画ファイルはシミュレーション時刻に対して等速です。')
            self.tick()
        except Exception as exc:
            self.stop()
            messagebox.showerror('実行エラー',str(exc))

    def tick(self):
        self.scheduled = None
        if self.sim is None:
            return
        self.sim.step()
        self.display(frame(self.sim,self.scenario,self.inference,self.decision,self.slots))
        done = self.sim.arrived or self.sim.failed or (not self.sim.path and self.sim.elapsed>4)
        if done:
            if self.auto_index is not None:
                self.scheduled = self.root.after(3000,self.next_case)
        else:
            self.scheduled = self.root.after(10,self.tick)

    def next_case(self):
        self.scheduled = None
        self.sim.close()
        self.sim = None
        self.auto_index += 1
        if self.auto_index < len(SCENARIOS):
            self.begin(SCENARIOS[self.auto_index],DEMO_SLOTS)
        else:
            self.auto_index = None
            self.display(title_card(True,self.classifier.evaluate()))

    def close(self):
        self.stop()
        self.root.destroy()


if __name__ == '__main__':
    ParkingApp().root.mainloop()
