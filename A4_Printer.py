import sys, os, re, base64, html, traceback, datetime
from io import BytesIO

LOG_FILE = os.path.join(os.path.dirname(__file__), "debug_log.txt")

def log(msg):
    ts = datetime.datetime.now().strftime("%H:%M:%S.%f")[:-3]
    line = f"[{ts}] {msg}"
    try:
        print(line)
    except:
        print(line.encode('ascii', 'replace').decode())
    with open(LOG_FILE, "a", encoding="utf-8") as f:
        f.write(line + "\n")

def log_err(e):
    log(f"ERROR: {e}")
    traceback.print_exc()
    with open(LOG_FILE, "a", encoding="utf-8") as f:
        traceback.print_exc(file=f)

try:
    from PyQt6.QtWidgets import (QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
                                 QLabel, QPushButton, QSpinBox, QComboBox, QTableWidget,
                                 QTableWidgetItem, QHeaderView, QFileDialog, QMessageBox,
                                 QGroupBox, QSplitter, QAbstractItemView, QDialog)
    from PyQt6.QtCore import Qt, QPoint
    from PyQt6.QtGui import QColor, QImage, QPixmap, QPainter, QFont, QMouseEvent, QPen
    log("PyQt6 imported OK")
except Exception as e:
    log_err(e); sys.exit(1)

try:
    from PIL import Image, ImageDraw, ImageFont, ImageEnhance
    import arabic_reshaper
    from bidi.algorithm import get_display
    log("PIL + arabic_reshaper imported OK")
except Exception as e:
    log_err(e); sys.exit(1)

log(f"Python {sys.version}")
log(f"CWD: OK")

# Clear old log
with open(LOG_FILE, "w", encoding="utf-8") as f:
    f.write(f"=== DEBUG LOG {datetime.datetime.now()} ===\n")

STYLE = """
QMainWindow, QWidget { background-color: #0f0f1a; color: #e0e0e0; }
QGroupBox { background-color: #1a1a2e; border: 1px solid #2a2a4a; border-radius: 10px;
            margin-top: 12px; padding: 18px 12px 12px 12px; font-size: 12px; font-weight: bold; color: #00d4aa; }
QGroupBox::title { subcontrol-origin: margin; left: 18px; padding: 0 8px; }
QPushButton { background-color: #6c5ce7; color: white; border: none; border-radius: 8px;
              padding: 10px 18px; font-size: 12px; font-weight: bold; }
QPushButton:hover { background-color: #a29bfe; }
QPushButton#green { background-color: #00b894; }
QPushButton#cyan { background-color: #00cec9; }
QPushButton#red { background-color: #e17055; }
QPushButton#orange { background-color: #fdcb6e; color: #2d3436; }
QPushButton#blue { background-color: #0984e3; }
QTableWidget { background-color: #1a1a2e; border: 1px solid #2a2a4a; border-radius: 8px;
               gridline-color: #2a2a4a; font-size: 11px; selection-background-color: #6c5ce7; }
QHeaderView::section { background-color: #6c5ce7; color: white; padding: 10px; border: none;
                       font-size: 11px; font-weight: bold; }
QSpinBox, QComboBox { background-color: #1a1a2e; color: white; border: 1px solid #2a2a4a;
                      border-radius: 6px; padding: 6px 10px; font-size: 11px; }
QComboBox QAbstractItemView { background-color: #1a1a2e; color: white; selection-background-color: #6c5ce7; }
QStatusBar { background-color: #1a1a2e; color: #00d4aa; font-weight: bold; font-size: 12px; }
"""


def pil_to_qpixmap(pil_img):
    log(f"  pil_to_qpixmap: mode={pil_img.mode} size={pil_img.size}")
    try:
        if pil_img.mode != 'RGB':
            pil_img = pil_img.convert('RGB')
        w, h = pil_img.width, pil_img.height
        bpl = 3 * w
        data = pil_img.tobytes()
        qimg = QImage(data, w, h, bpl, QImage.Format.Format_RGB888)
        pm = QPixmap.fromImage(qimg)
        log(f"  pil_to_qpixmap: OK {pm.width()}x{pm.height()}")
        return pm
    except Exception as e:
        log_err(e)
        return None


class EditorCanvas(QLabel):
    def __init__(self):
        super().__init__()
        self.setFixedSize(590, 830)
        self.setStyleSheet("background:#1a1a2e; border:2px solid #6c5ce7;")
        self.setMouseTracking(True)
        self.move_targets = {}
        self.resize_targets = {}
        self.drag_target = None
        self.drag_type = None
        self.drag_off = QPoint()
        self.drag_sz0 = 0
        self.on_change = None
        self.text_zones = {}
        log("EditorCanvas created")

    def set_data(self, move_t, resize_t, text_zones=None):
        self.move_targets = move_t or {}
        self.resize_targets = resize_t or {}
        self.text_zones = text_zones or {}
        self.update()

    def get_zone_handles(self, zone):
        x, y, w, h = zone['x'], zone['y'], zone['w'], zone['h']
        return {
            'tc': (x+w//2, y), 'tr': (x+w, y),
            'ml': (x, y+h//2), 'mr': (x+w, y+h//2),
            'bl': (x, y+h), 'bc': (x+w//2, y+h), 'br': (x+w, y+h),
        }

    def paintEvent(self, e):
        super().paintEvent(e)
        try:
            p = QPainter(self)
            colors = {'number': QColor('#ff6d00'), 'title': QColor('#6c5ce7'), 'summary': QColor('#00cec9')}
            for name, pos in self.move_targets.items():
                px, py = int(pos['x']), int(pos['y'])
                p.setBrush(colors.get(name, QColor('yellow')))
                p.setPen(QColor('white'))
                p.drawEllipse(QPoint(px, py), 14, 14)
                p.setPen(QColor('white'))
                p.setFont(QFont('Segoe UI', 9, QFont.Weight.Bold))
                p.drawText(px, py-22, name.upper())
            for name, pos in self.resize_targets.items():
                px, py = int(pos['x']), int(pos['y'])
                p.setBrush(colors.get(name, QColor('yellow')))
                p.setPen(QColor('white'))
                p.drawRect(px-15, py-12, 30, 24)
                p.setPen(QColor('white'))
                p.setFont(QFont('Consolas', 10, QFont.Weight.Bold))
                p.drawText(px, py+25, str(pos.get('sz', 0)))
                p.setFont(QFont('Segoe UI', 8, QFont.Weight.Bold))
                p.drawText(px-28, py+4, name[:3].upper())
            for name, zone in self.text_zones.items():
                x, y, w, h = zone['x'], zone['y'], zone['w'], zone['h']
                p.setPen(QPen(QColor(colors.get(name, '#ffffff')), 2, Qt.PenStyle.DashLine))
                p.setBrush(QColor(0, 0, 0, 0))
                p.drawRect(x, y, w, h)
                handles = self.get_zone_handles(zone)
                for hn, (hx, hy) in handles.items():
                    p.setBrush(QColor('white'))
                    p.setPen(QColor(colors.get(name, '#ffffff')))
                    p.drawRect(hx-7, hy-7, 14, 14)
                p.setPen(QColor('white'))
                p.setFont(QFont('Segoe UI', 8))
                p.drawText(x+w+5, y+h//2+4, name)
            p.end()
        except Exception as e:
            log_err(e)

    def mousePressEvent(self, e: QMouseEvent):
        try:
            x, y = int(e.position().x()), int(e.position().y())
            log(f"mousePress: x={x} y={y}")

            for name, zone in self.text_zones.items():
                handles = self.get_zone_handles(zone)
                for hn, (hx, hy) in handles.items():
                    if abs(x-hx) <= 15 and abs(y-hy) <= 15:
                        self.drag_target = name
                        self.drag_type = f'text_{hn}'
                        self.drag_off = QPoint(x, y)
                        self.drag_zone = zone.copy()
                        log(f"  -> text handle: {name} {hn} zone={zone}")
                        return

            for name, pos in self.resize_targets.items():
                rx, ry = int(pos['x']), int(pos['y'])
                if abs(x-rx) <= 20 and abs(y-ry) <= 20:
                    self.drag_target = name
                    self.drag_type = 'resize'
                    self.drag_sz0 = pos.get('sz', 50)
                    self.drag_off = QPoint(x, y)
                    log(f"  -> resize target: {name}")
                    return

            for name, pos in self.move_targets.items():
                mx, my = int(pos['x']), int(pos['y'])
                if abs(x-mx) <= 30 and abs(y-my) <= 30:
                    self.drag_target = name
                    self.drag_type = 'move'
                    self.drag_off = QPoint(x-mx, y-my)
                    log(f"  -> move target: {name}")
                    return
            log("  -> no target hit")
        except Exception as e:
            log_err(e)

    def mouseMoveEvent(self, e: QMouseEvent):
        if not self.drag_target or not self.on_change:
            return
        try:
            x, y = int(e.position().x()), int(e.position().y())
            if self.drag_type == 'move':
                nx = max(0, min(570, x - self.drag_off.x()))
                ny = max(0, min(810, y - self.drag_off.y()))
                self.on_change('move', self.drag_target, nx, ny)
            elif self.drag_type == 'resize':
                delta = y - self.drag_off.y()
                nsz = max(10, min(200, int(self.drag_sz0 + delta * 0.5)))
                self.on_change('resize', self.drag_target, nsz)
            elif self.drag_type.startswith('text_'):
                handle = self.drag_type.replace('text_', '')
                dx = x - self.drag_off.x()
                dy = y - self.drag_off.y()
                if handle in ('ml', 'mr', 'tl', 'tr', 'bl', 'br'):
                    nw = max(50, min(570, int(self.drag_zone.get('w', 530) + dx * 0.5)))
                    nsz = max(10, min(80, int(self.drag_zone.get('sz', 50) + dy * 0.3)))
                    self.on_change('text_resize', self.drag_target, nw, nsz)
                elif handle in ('tc', 'bc'):
                    nx = max(0, min(570, x))
                    ny = max(0, min(810, y))
                    self.on_change('text_move', self.drag_target, nx, ny)
        except Exception as e:
            log_err(e)

    def mouseReleaseEvent(self, e):
        log(f"mouseRelease: was dragging {self.drag_target} type={self.drag_type}")
        self.drag_target = None
        self.drag_type = None
        self.drag_zone = None


class PosterStudio(QMainWindow):
    def __init__(self):
        super().__init__()
        log("PosterStudio.__init__ start")
        self.setWindowTitle("A4 Poster Studio - DEBUG")
        self.setMinimumSize(1350, 880)
        self.items = []
        self.start_number = 1
        self.number_size = 80
        self.title_size = 36
        self.summary_size = 22
        self.number_position = 'top-right'
        self.title_position = 'bottom'
        self.summary_position = 'bottom'
        self.custom_positions = None
        self.custom_text_width = {'title': 530, 'summary': 530}
        self.text_align = {'title': 'right', 'summary': 'right'}
        self.text_positions = {'title': {'x': 30, 'y': 650}, 'summary': {'x': 30, 'y': 730}}
        self.editor_idx = 0
        self.setup_ui()
        log("PosterStudio.__init__ done")

    def setup_ui(self):
        central = QWidget()
        self.setCentralWidget(central)
        layout = QHBoxLayout(central)
        layout.setSpacing(12)
        layout.setContentsMargins(16, 16, 16, 16)
        splitter = QSplitter(Qt.Orientation.Horizontal)
        layout.addWidget(splitter)

        left = QWidget()
        ll = QVBoxLayout(left)
        ll.setContentsMargins(0, 0, 0, 0)
        tb = QHBoxLayout()
        for text, slot, color in [("+ HTML", self.add_file, "green"), ("+ Folder", self.add_folder, "cyan"),
                                   ("Up", self.move_up, "blue"), ("Down", self.move_down, "blue"),
                                   ("Delete", self.delete_sel, "red"), ("Clear", self.clear_all, "red")]:
            b = QPushButton(text); b.setObjectName(color); b.setFixedHeight(34); b.clicked.connect(slot)
            tb.addWidget(b)
        ll.addLayout(tb)

        self.table = QTableWidget()
        self.table.setColumnCount(4)
        self.table.setHorizontalHeaderLabels(["#", "Movie Title", "Title", "Summary"])
        self.table.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeMode.Stretch)
        self.table.horizontalHeader().setSectionResizeMode(3, QHeaderView.ResizeMode.Stretch)
        self.table.setColumnWidth(0, 50); self.table.setColumnWidth(2, 70)
        self.table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self.table.doubleClicked.connect(self.dbl_click)
        ll.addWidget(self.table)
        splitter.addWidget(left)

        right = QWidget(); right.setMaximumWidth(310)
        rl = QVBoxLayout(right); rl.setContentsMargins(0, 0, 0, 0)

        g1 = QGroupBox("SETTINGS")
        s1 = QVBoxLayout()
        for label, attr, mn, mx, dv in [("Start", "sp_start", 1, 9999, 1),
                                          ("Number Size", "sp_num", 30, 200, 80),
                                          ("Title Size", "sp_title", 16, 80, 36),
                                          ("Summary Size", "sp_summ", 10, 50, 22)]:
            row = QHBoxLayout(); row.addWidget(QLabel(label))
            sp = QSpinBox(); sp.setRange(mn, mx); sp.setValue(dv); setattr(self, attr, sp)
            row.addWidget(sp); s1.addLayout(row)
        g1.setLayout(s1); rl.addWidget(g1)

        g2 = QGroupBox("POSITIONS")
        s2 = QVBoxLayout()
        self.cb_numpos = QComboBox(); self.cb_numpos.addItems(["top-right", "top-left", "bottom-right", "bottom-left"])
        s2.addWidget(QLabel("Number:")); s2.addWidget(self.cb_numpos)
        self.cb_titlepos = QComboBox(); self.cb_titlepos.addItems(["top", "bottom", "center"])
        s2.addWidget(QLabel("Title:")); s2.addWidget(self.cb_titlepos)
        self.cb_summpos = QComboBox(); self.cb_summpos.addItems(["top", "bottom", "center"])
        s2.addWidget(QLabel("Summary:")); s2.addWidget(self.cb_summpos)
        g2.setLayout(s2); rl.addWidget(g2)

        g3 = QGroupBox("ACTIONS")
        s3 = QVBoxLayout()
        for text, slot, color in [("Preview", self.preview, "cyan"), ("EDITOR", self.open_editor, ""),
                                   ("Save PNG", self.save_png, "blue"), ("Save PDF", self.save_pdf, "blue"),
                                   ("Print", self.do_print, "orange")]:
            b = QPushButton(text)
            if color: b.setObjectName(color)
            b.setFixedHeight(38); b.clicked.connect(slot); s3.addWidget(b)
        g3.setLayout(s3); rl.addWidget(g3); rl.addStretch()
        splitter.addWidget(right); splitter.setSizes([900, 310])
        self.statusBar().showMessage("  DEBUG  |  0/16")

    def add_file(self):
        log("add_file")
        try:
            p, _ = QFileDialog.getOpenFileName(self, "Select HTML", "", "HTML (*.html *.htm)")
            if p: self.process(p)
        except Exception as e: log_err(e)

    def add_folder(self):
        log("add_folder")
        try:
            p = QFileDialog.getExistingDirectory(self, "Select Folder")
            if p:
                for f in sorted(os.listdir(p)):
                    if f.lower().endswith(('.html', '.htm')):
                        self.process(os.path.join(p, f))
        except Exception as e: log_err(e)

    def process(self, path):
        log(f"process: {path}")
        try:
            if len(self.items) >= 16:
                return log("Max 16!")
            with open(path, 'r', encoding='utf-8') as f:
                c = f.read()
            t = re.search(r'<div class="hero-title">(.*?)</div>', c, re.DOTALL)
            t = html.unescape(t.group(1).strip()) if t else "No Title"
            m = re.search(r'<img\s+src="(data:image/[^;]+;base64,[^"]+)"', c)
            if not m: return log("No image found")
            _, d = m.group(1).split(',', 1)
            img = Image.open(BytesIO(base64.b64decode(d))).convert('RGB')
            s = re.search(r'<div class="plot-text">(.*?)</div>', c, re.DOTALL)
            s = html.unescape(re.sub(r'<[^>]+>', '', s.group(1).strip())) if s else ''
            self.items.append({'title': t, 'image': img, 'summary': s, 'show_title': False})
            log(f"  added: {t} ({img.size})")
            self.refresh()
        except Exception as e: log_err(e)

    def refresh(self):
        self.table.setRowCount(len(self.items))
        for i, item in enumerate(self.items):
            self.table.setItem(i, 0, QTableWidgetItem(str(self.start_number+i)))
            self.table.setItem(i, 1, QTableWidgetItem(item['title']))
            si = QTableWidgetItem("ON" if item.get('show_title') else "OFF")
            si.setForeground(QColor('#00e676') if item.get('show_title') else QColor('#ff5252'))
            self.table.setItem(i, 2, si)
            self.table.setItem(i, 3, QTableWidgetItem(item.get('summary','')[:50]))
        self.statusBar().showMessage(f"  DEBUG  |  {len(self.items)}/16")

    def clear_all(self):
        self.items.clear(); self.refresh()

    def delete_sel(self):
        rows = sorted(set(i.row() for i in self.table.selectedIndexes()), reverse=True)
        for r in rows:
            if 0 <= r < len(self.items): del self.items[r]
        self.refresh()

    def dbl_click(self, idx):
        if idx.column() == 2 and 0 <= idx.row() < len(self.items):
            self.items[idx.row()]['show_title'] = not self.items[idx.row()].get('show_title', False)
            self.refresh()

    def move_up(self):
        r = self.table.currentRow()
        if r > 0:
            self.items[r], self.items[r-1] = self.items[r-1], self.items[r]
            self.refresh()

    def move_down(self):
        r = self.table.currentRow()
        if 0 <= r < len(self.items)-1:
            self.items[r], self.items[r+1] = self.items[r+1], self.items[r]
            self.refresh()

    def gfont(self, sz):
        for p in ["C:/Windows/Fonts/tahoma.ttf", "C:/Windows/Fonts/arial.ttf"]:
            try: return ImageFont.truetype(p, sz)
            except: pass
        return ImageFont.load_default()

    def gbold(self, sz):
        for p in ["C:/Windows/Fonts/tahomabd.ttf", "C:/Windows/Fonts/arialbd.ttf"]:
            try: return ImageFont.truetype(p, sz)
            except: pass
        return self.gfont(sz)

    def reshape(self, t):
        return get_display(arabic_reshaper.reshape(t))

    def dshadow(self, d, pos, t, f, fill='white', s='black', o=2):
        d.text((pos[0]+o, pos[1]+o), t, fill=s, font=f)
        d.text(pos, t, fill=fill, font=f)

    def wrap_rtl(self, text, font, mw, d):
        words = text.split()
        lines, cur = [], ""
        for w in words:
            test = w + " " + cur if cur else w
            if d.textbbox((0,0), test, font=font)[2] <= mw:
                cur = test
            else:
                if cur: lines.append(cur)
                cur = w
        if cur: lines.append(cur)
        return lines

    def build_page(self):
        log("build_page")
        W, H, M, G = 2480, 3508, 40, 30
        cw, ch = (W-5*M)//4, (H-5*M)//4
        page = Image.new('RGB', (W, H), 'black')
        for i, item in enumerate(self.items[:16]):
            r, c = i//4, i%4
            x, y = M+c*(cw+G), M+r*(ch+G)
            img = item['image'].copy().resize((cw, ch), Image.Resampling.LANCZOS)
            img = ImageEnhance.Brightness(img).enhance(0.7)
            page.paste(img, (x, y))
            ov = Image.new('RGBA', (cw, ch), (0,0,0,0))
            od = ImageDraw.Draw(ov)
            for gy in range(ch//3):
                od.line([(0,ch-gy),(cw,ch-gy)], fill=(0,0,0,int(180*(1-gy/(ch//3)))))
            page.paste(Image.alpha_composite(page.crop((x,y,x+cw,y+ch)).convert('RGBA'), ov).convert('RGB'), (x,y))
            draw = ImageDraw.Draw(page)

            # Number
            nt = str(self.start_number+i)
            nf = self.gbold(self.number_size)
            if self.custom_positions:
                sx, sy = cw/590, ch/830
                nx = x+int(self.custom_positions['number']['x']*sx)
                ny = y+int(self.custom_positions['number']['y']*sy)
            else:
                bbox = draw.textbbox((0,0),nt,font=nf)
                nw = bbox[2]-bbox[0]
                nx = x+(cw-nw-20); ny = y+15
            bbox = draw.textbbox((0,0),nt,font=nf)
            nw = bbox[2]-bbox[0]
            draw.rounded_rectangle([nx-15,ny-10,nx+nw+15,ny+15], radius=10, fill=(200,30,30))
            self.dshadow(draw,(nx,ny),nt,nf,'white','darkred',2)

            # Title
            if item.get('show_title') and item.get('title'):
                tf = self.gbold(self.title_size)
                tw = self.custom_text_width.get('title', cw-60)
                lines = self.wrap_rtl(item['title'], tf, tw, draw)
                p2 = self.text_positions['title']
                tx = x+int(p2['x'])
                ty = y+int(p2['y'])
                talign = self.text_align.get('title', 'right')
                for j, line in enumerate(lines):
                    line = self.reshape(line)
                    lw = draw.textbbox((0,0),line,font=tf)[2]
                    if talign == 'right': lx = tx+tw-lw
                    elif talign == 'center': lx = tx+(tw-lw)//2
                    else: lx = tx
                    draw.text((lx, ty+j*(self.title_size+5)), line, fill='white', font=tf)

            # Summary
            if item.get('summary'):
                sf = self.gfont(self.summary_size)
                sw = self.custom_text_width.get('summary', cw-60)
                lines = self.wrap_rtl(item['summary'], sf, sw, draw)
                p3 = self.text_positions['summary']
                sxx = x+int(p3['x'])
                syy = y+int(p3['y'])
                salign = self.text_align.get('summary', 'right')
                for j, line in enumerate(lines):
                    line = self.reshape(line)
                    lw = draw.textbbox((0,0),line,font=sf)[2]
                    if salign == 'right': lx = sxx+sw-lw
                    elif salign == 'center': lx = sxx+(sw-lw)//2
                    else: lx = sxx
                    ly = syy+j*(self.summary_size+3)
                    if ly < ch - 10:
                        draw.text((lx, ly), line, fill=(200,200,200), font=sf)

            draw.rectangle([x,y,x+cw-1,y+ch-1], outline=(50,50,50), width=2)
        log("build_page done")
        return page

    def preview(self):
        if not self.items: return
        try:
            pg = self.build_page()
            win = QDialog(self); win.setWindowTitle("Preview"); lay = QVBoxLayout(win)
            lbl = QLabel()
            ph = 800; pw = int(ph*2480/3508)
            resized = pg.copy(); resized.thumbnail((pw, ph), Image.Resampling.LANCZOS)
            pm = pil_to_qpixmap(resized)
            if pm:
                lbl.setPixmap(pm)
                lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
            lay.addWidget(lbl)
            win.setMinimumSize(pw+20, ph+60)
            win.exec()
        except Exception as e: log_err(e)

    def save_png(self):
        if not self.items: return
        p, _ = QFileDialog.getSaveFileName(self, "Save", "", "PNG (*.png)")
        if p:
            self.build_page().save(p, quality=95)
            log(f"Saved PNG: {p}")

    def save_pdf(self):
        if not self.items: return
        p, _ = QFileDialog.getSaveFileName(self, "Save", "", "PDF (*.pdf)")
        if p:
            self.build_page().save(p, "PDF", resolution=300)
            log(f"Saved PDF: {p}")

    def do_print(self):
        if not self.items: return
        p = os.path.join(os.environ['TEMP'], 'a4_print.png')
        self.build_page().save(p, quality=95)
        os.startfile(p, 'print')

    def open_editor(self):
        log("="*40)
        log("open_editor CALLED")
        log(f"  items count: {len(self.items)}")
        try:
            if not self.items:
                return

            if not self.custom_positions:
                self.custom_positions = {'number': {'x': 480, 'y': 20}}

            dlg = QDialog(self)
            dlg.setWindowTitle("Editor - DEBUG")
            dlg.setMinimumSize(730, 980)
            lay = QVBoxLayout(dlg)

            lbl = QLabel(f"Image 1 / {len(self.items)}")
            lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
            lbl.setStyleSheet("font-size:14px; font-weight:bold; color:white;")
            lay.addWidget(lbl)

            canvas_lbl = QLabel()
            canvas_lbl.setFixedSize(590, 830)
            canvas_lbl.setStyleSheet("background:#1a1a2e; border:2px solid #6c5ce7;")
            canvas_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
            lay.addWidget(canvas_lbl, alignment=Qt.AlignmentFlag.AlignCenter)

            canvas_overlay = EditorCanvas()
            canvas_overlay.setParent(canvas_lbl)
            canvas_overlay.move(0, 0)
            canvas_overlay.setStyleSheet("background:transparent; border:none;")

            def draw_in_editor():
                try:
                    idx = self.editor_idx if hasattr(self, 'editor_idx') else 0
                    item = self.items[idx]
                    log(f"draw_in_editor: idx={idx} title={item['title']}")
                    cw, ch = 590, 830
                    img = item['image'].copy().resize((cw, ch), Image.Resampling.LANCZOS)
                    img = ImageEnhance.Brightness(img).enhance(0.7)
                    ov = Image.new('RGBA', (cw, ch), (0,0,0,0))
                    od = ImageDraw.Draw(ov)
                    for gy in range(ch//3):
                        od.line([(0,ch-gy),(cw,ch-gy)], fill=(0,0,0,int(180*(1-gy/(ch//3)))))
                    base = Image.alpha_composite(img.copy().convert('RGBA'), ov).convert('RGB')
                    draw = ImageDraw.Draw(base)

                    colors_d = {'number': '#ff6d00', 'title': '#6c5ce7', 'summary': '#00cec9'}
                    sizes = {'number': self.number_size, 'title': self.title_size, 'summary': self.summary_size}

                    # Number
                    nt = str(self.start_number + idx)
                    nf = self.gbold(self.number_size)
                    p = self.custom_positions['number']
                    px, py = int(p['x']), int(p['y'])
                    bbox = draw.textbbox((0,0), nt, font=nf)
                    nw, nh = bbox[2]-bbox[0], bbox[3]-bbox[1]
                    draw.rounded_rectangle([px-15,py-10,px+nw+15,py+nh+10], radius=10, fill=(200,30,30))
                    draw.text((px,py), nt, fill='white', font=nf)

                    # Title
                    if item.get('show_title') and item.get('title'):
                        tf = self.gbold(self.title_size)
                        p2 = self.text_positions['title']
                        px2, py2 = int(p2['x']), int(p2['y'])
                        tw = self.custom_text_width.get('title', cw-60)
                        lines = self.wrap_rtl(item['title'], tf, tw, draw)
                        talign = self.text_align.get('title', 'right')
                        for j, line in enumerate(lines):
                            line = self.reshape(line)
                            lw = draw.textbbox((0,0),line,font=tf)[2]
                            if talign == 'right':
                                lx = px2 + tw - lw
                            elif talign == 'center':
                                lx = px2 + (tw - lw) // 2
                            else:
                                lx = px2
                            draw.text((lx, py2+j*(self.title_size+5)), line, fill='white', font=tf)

                    # Summary
                    if item.get('summary'):
                        sf = self.gfont(self.summary_size)
                        p3 = self.text_positions['summary']
                        px3, py3 = int(p3['x']), int(p3['y'])
                        sw = self.custom_text_width.get('summary', cw-60)
                        lines = self.wrap_rtl(item['summary'], sf, sw, draw)
                        salign = self.text_align.get('summary', 'right')
                        for j, line in enumerate(lines):
                            line = self.reshape(line)
                            lw = draw.textbbox((0,0),line,font=sf)[2]
                            if salign == 'right':
                                lx = px3 + sw - lw
                            elif salign == 'center':
                                lx = px3 + (sw - lw) // 2
                            else:
                                lx = px3
                            draw.text((lx, py3+j*(self.summary_size+3)), line, fill=(200,200,200), font=sf)

                    # Move handles
                    for nm, ps in self.custom_positions.items():
                        draw.ellipse([int(ps['x'])-14, int(ps['y'])-14, int(ps['x'])+14, int(ps['y'])+14],
                                    fill=colors_d.get(nm,'yellow'), outline='white', width=2)

                    # Resize handles
                    y_pos = {'number': 60, 'title': 380, 'summary': 520}
                    resize_t = {}
                    for nm in ['number','title','summary']:
                        ry = y_pos[nm]
                        draw.rectangle([540,ry-12,575,ry+12], fill=colors_d[nm], outline='white', width=2)
                        draw.text((558,ry+25), str(sizes[nm]), fill=colors_d[nm], font=self.gbold(10))
                        resize_t[nm] = {'x':557, 'y':ry, 'sz':sizes[nm]}

                    # Text zones for direct drag resize
                    text_zones = {}
                    if item.get('title'):
                        tf = self.gbold(self.title_size)
                        tw = self.custom_text_width.get('title', cw-60)
                        tlines = self.wrap_rtl(item['title'], tf, tw, draw)
                        p2 = self.text_positions['title']
                        th = len(tlines) * (self.title_size + 5)
                        text_zones['title'] = {'x': int(p2['x']), 'y': int(p2['y']), 'w': tw, 'h': th, 'sz': self.title_size}
                    if item.get('summary'):
                        sf = self.gfont(self.summary_size)
                        sw = self.custom_text_width.get('summary', cw-60)
                        slines = self.wrap_rtl(item['summary'], sf, sw, draw)
                        p3 = self.text_positions['summary']
                        sh = len(slines) * (self.summary_size + 3)
                        text_zones['summary'] = {'x': int(p3['x']), 'y': int(p3['y']), 'w': sw, 'h': sh, 'sz': self.summary_size}

                    log(f"  drawing image {base.size}")
                    pm = pil_to_qpixmap(base)
                    if pm:
                        canvas_lbl.setPixmap(pm)
                        log("  pixmap set on canvas_lbl OK")
                    else:
                        log("  ERROR: pixmap is None!")

                    canvas_overlay.set_data(self.custom_positions.copy(), resize_t, text_zones)
                    log("  overlay updated OK")

                except Exception as e:
                    log(f"  draw_in_editor EXCEPTION: {e}")
                    log_err(e)

            def on_canvas_change(mode, name, val1, val2=None):
                try:
                    if mode == 'move':
                        if name in ('title', 'summary'):
                            self.text_positions[name] = {'x': val1, 'y': val2}
                        else:
                            self.custom_positions[name] = {'x': val1, 'y': val2}
                    elif mode == 'resize':
                        if name == 'number':
                            self.number_size = max(30, min(200, val1))
                            self.sp_num.setValue(self.number_size)
                        elif name == 'title':
                            self.title_size = max(16, min(80, val1))
                            self.sp_title.setValue(self.title_size)
                        elif name == 'summary':
                            self.summary_size = max(10, min(50, val1))
                            self.sp_summ.setValue(self.summary_size)
                    elif mode == 'text_resize':
                        if name == 'title':
                            self.custom_text_width['title'] = max(100, min(570, val1))
                            if val2 is not None:
                                self.title_size = max(16, min(80, val2))
                                self.sp_title.setValue(self.title_size)
                        elif name == 'summary':
                            self.custom_text_width['summary'] = max(100, min(570, val1))
                            if val2 is not None:
                                self.summary_size = max(10, min(50, val2))
                                self.sp_summ.setValue(self.summary_size)
                    elif mode == 'text_move':
                        self.text_positions[name] = {'x': val1, 'y': val2}
                    draw_in_editor()
                except Exception as e:
                    log_err(e)

            canvas_overlay.on_change = on_canvas_change

            self.editor_idx = 0

            def next_img():
                if self.editor_idx < len(self.items)-1:
                    self.editor_idx += 1
                    lbl.setText(f"Image {self.editor_idx+1} / {len(self.items)}")
                    draw_in_editor()

            def prev_img():
                if self.editor_idx > 0:
                    self.editor_idx -= 1
                    lbl.setText(f"Image {self.editor_idx+1} / {len(self.items)}")
                    draw_in_editor()

            nav = QHBoxLayout()
            bp = QPushButton("<"); bp.setFixedWidth(50)
            bn = QPushButton(">"); bn.setFixedWidth(50)
            bp.clicked.connect(prev_img); bn.clicked.connect(next_img)
            nav.addWidget(bp); nav.addWidget(lbl); nav.addWidget(bn)
            lay.addLayout(nav)

            sf = QHBoxLayout()
            for label, attr, mn, mx in [("Number","sp_num",30,200),("Title","sp_title",16,80),("Summary","sp_summ",10,50)]:
                sf.addWidget(QLabel(f"{label}:"))
                bd = QPushButton("-"); bd.setFixedWidth(35); bd.setStyleSheet("background:#e17055;")
                sp = getattr(self, attr)
                sp.valueChanged.connect(draw_in_editor)
                bd.clicked.connect(lambda c, sp=sp, v=mn: sp.setValue(max(v, sp.value()-2)))
                sf.addWidget(bd); sf.addWidget(sp)
                bi = QPushButton("+"); bi.setFixedWidth(35); bi.setStyleSheet("background:#00b894;")
                bi.clicked.connect(lambda c, sp=sp, v=mx: sp.setValue(min(v, sp.value()+2)))
                sf.addWidget(bi)
            lay.addLayout(sf)

            af = QHBoxLayout()
            af.addWidget(QLabel("Title Align:"))
            for align, label in [("right", "R"), ("center", "C"), ("left", "L")]:
                btn = QPushButton(label)
                btn.setFixedWidth(35)
                btn.setStyleSheet("background:#6c5ce7;" if self.text_align.get('title') == align else "background:#333;")
                btn.clicked.connect(lambda c, a=align: [self.text_align.__setitem__('title', a), draw_in_editor()])
                af.addWidget(btn)
            af.addSpacing(20)
            af.addWidget(QLabel("Summary Align:"))
            for align, label in [("right", "R"), ("center", "C"), ("left", "L")]:
                btn = QPushButton(label)
                btn.setFixedWidth(35)
                btn.setStyleSheet("background:#00cec9;" if self.text_align.get('summary') == align else "background:#333;")
                btn.clicked.connect(lambda c, a=align: [self.text_align.__setitem__('summary', a), draw_in_editor()])
                af.addWidget(btn)
            lay.addLayout(af)

            bc = QPushButton("Close"); bc.setStyleSheet("background:#e17055;")
            def close_editor():
                for sp_attr in ['sp_num', 'sp_title', 'sp_summ']:
                    try:
                        sp = getattr(self, sp_attr)
                        sp.valueChanged.disconnect()
                    except:
                        pass
                dlg.close()
            bc.clicked.connect(close_editor)
            lay.addWidget(bc)

            draw_in_editor()
            dlg.exec()

        except Exception as e:
            log(f"open_editor FATAL: {e}")
            log_err(e)


if __name__ == "__main__":
    log("="*60)
    log("A4 Poster Studio - DEBUG MODE")
    log("="*60)
    try:
        app = QApplication(sys.argv)
        log("QApplication OK")
        app.setStyleSheet(STYLE)
        w = PosterStudio()
        log("Window created, showing...")
        w.show()
        log("Window shown, entering main loop...")
        sys.exit(app.exec())
    except Exception as e:
        log(f"FATAL: {e}")
        log_err(e)
