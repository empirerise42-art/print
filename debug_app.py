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
        self.text_zones = {}
        self.drag_target = None
        self.drag_type = None
        self.drag_off = QPoint()
        self.drag_sz0 = 0
        self.on_change = None
        self.pil_image = None

    def set_data(self, move_t, resize_t, text_zones=None):
        self.move_targets = move_t or {}
        self.resize_targets = resize_t or {}
        self.text_zones = text_zones or {}
        self.update()

    def set_pil_image(self, pil_img):
        self.pil_image = pil_img
        try:
            pm = pil_to_qpixmap(pil_img)
            if pm:
                self.setPixmap(pm)
        except Exception as e:
            log(f"set_pil_image error: {e}")

    def paintEvent(self, e):
        super().paintEvent(e)

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

                # Move handle (circle at top-left)
                p.setBrush(QColor(colors.get(name, '#ffffff')))
                p.setPen(QPen(QColor('white'), 2))
                p.drawEllipse(QPoint(x, y), 12, 12)
                p.setPen(QColor('white'))
                p.setFont(QFont('Segoe UI', 7))
                p.drawText(x - 30, y + 4, name)

                # Resize handles (squares at corners and midpoints)
                handles = self.get_zone_handles(zone)
                for hn, (hx, hy) in handles.items():
                    p.setBrush(QColor('white'))
                    p.setPen(QPen(QColor(colors.get(name, '#ffffff')), 2))
                    p.drawRect(hx-10, hy-10, 20, 20)
            p.end()
        except Exception as e:
            log_err(e)

    def mousePressEvent(self, e: QMouseEvent):
        try:
            x, y = int(e.position().x()), int(e.position().y())
            log(f"mousePress: x={x} y={y}")

            for name, zone in self.text_zones.items():
                xz, yz, wz, hz = zone['x'], zone['y'], zone['w'], zone['h']

                # Check move handle (circle at top-left)
                if abs(x - xz) <= 15 and abs(y - yz) <= 15:
                    self.drag_target = name
                    self.drag_type = 'text_move'
                    self.drag_off = QPoint(x - xz, y - yz)
                    self.drag_zone = zone.copy()
                    log(f"  -> text move: {name}")
                    return

                # Check resize handles
                handles = self.get_zone_handles(zone)
                for hn, (hx, hy) in handles.items():
                    if abs(x-hx) <= 20 and abs(y-hy) <= 20:
                        self.drag_target = name
                        self.drag_type = f'text_{hn}'
                        self.drag_off = QPoint(x, y)
                        self.drag_zone = zone.copy()
                        log(f"  -> text resize: {name} {hn}")
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
            elif self.drag_type == 'text_move':
                nx = max(0, min(570, x - self.drag_off.x()))
                ny = max(0, min(810, y - self.drag_off.y()))
                self.on_change('text_move', self.drag_target, nx, ny)
            elif self.drag_type.startswith('text_'):
                handle = self.drag_type.replace('text_', '')
                dx = x - self.drag_off.x()
                dy = y - self.drag_off.y()
                nw = max(50, min(570, int(self.drag_zone.get('w', 530) + dx * 0.5)))
                nsz = max(10, min(80, int(self.drag_zone.get('sz', 50) + dy * 0.5)))
                self.on_change('text_resize', self.drag_target, nw, nsz)
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
        self.per_image_settings = {}
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
        self.table.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.table.customContextMenuRequested.connect(self.context_menu)
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
            sp.valueChanged.connect(self.update_settings)
            row.addWidget(sp); s1.addLayout(row)
        g1.setLayout(s1); rl.addWidget(g1)

        g2 = QGroupBox("POSITIONS")
        s2 = QVBoxLayout()
        self.cb_numpos = QComboBox(); self.cb_numpos.addItems(["top-right", "top-left", "bottom-right", "bottom-left"])
        self.cb_numpos.currentTextChanged.connect(self.on_pos_change)
        s2.addWidget(QLabel("Number:")); s2.addWidget(self.cb_numpos)
        self.cb_titlepos = QComboBox(); self.cb_titlepos.addItems(["top", "bottom", "center"])
        self.cb_titlepos.currentTextChanged.connect(self.on_pos_change)
        s2.addWidget(QLabel("Title:")); s2.addWidget(self.cb_titlepos)
        self.cb_summpos = QComboBox(); self.cb_summpos.addItems(["top", "bottom", "center"])
        self.cb_summpos.currentTextChanged.connect(self.on_pos_change)
        s2.addWidget(QLabel("Summary:")); s2.addWidget(self.cb_summpos)
        g2.setLayout(s2); rl.addWidget(g2)

        g3 = QGroupBox("ACTIONS")
        s3 = QVBoxLayout()
        for text, slot, color in [("Preview", self.preview, "cyan"), ("Text Catalog", self.preview_text_catalog, "green"), ("9 Poster", self.preview_9poster, "orange"),
                                   ("EDITOR", self.open_editor, ""),
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
            genre_matches = re.findall(r'<span class="tag">(.*?)</span>', c)
            genre = ' | '.join([html.unescape(g.strip()) for g in genre_matches]) if genre_matches else ''
            year = re.search(r'<th>📅 سال</th><td>(.*?)</td>', c, re.DOTALL)
            year = html.unescape(re.sub(r'<[^>]+>', '', year.group(1).strip())) if year else ''
            self.items.append({'title': t, 'image': img, 'summary': s, 'genre': genre, 'year': year, 'show_title': False})
            log(f"  added: {t} | genre={genre} | year={year}")
            self.refresh()
        except Exception as e: log_err(e)

    def on_pos_change(self):
        self.number_position = self.cb_numpos.currentText()
        self.title_position = self.cb_titlepos.currentText()
        self.summary_position = self.cb_summpos.currentText()

    def update_settings(self):
        self.start_number = self.sp_start.value()
        self.number_size = self.sp_num.value()
        self.title_size = self.sp_title.value()
        self.summary_size = self.sp_summ.value()
        self.refresh()

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

    def context_menu(self, pos):
        from PyQt6.QtWidgets import QMenu
        idx = self.table.indexAt(pos)
        if idx.row() >= 0 and idx.row() < len(self.items):
            menu = QMenu(self)
            menu.addAction("روشن/خاموش عنوان", lambda: self.toggle_title(idx.row()))
            menu.addAction("حذف", lambda: self.delete_item(idx.row()))
            menu.exec(self.table.viewport().mapToGlobal(pos))

    def toggle_title(self, row):
        if 0 <= row < len(self.items):
            self.items[row]['show_title'] = not self.items[row].get('show_title', False)
            self.refresh()

    def delete_item(self, row):
        if 0 <= row < len(self.items):
            del self.items[row]
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
        for p in ["C:/Windows/Fonts/Vazir.ttf", "C:/Windows/Fonts/DIANAP.TTF", "C:/Windows/Fonts/tahoma.ttf", "C:/Windows/Fonts/arial.ttf"]:
            try: return ImageFont.truetype(p, sz)
            except: pass
        return ImageFont.load_default()

    def gbold(self, sz):
        for p in ["C:/Windows/Fonts/Vazir-Bold.ttf", "C:/Windows/Fonts/DIANAP.TTF", "C:/Windows/Fonts/tahomabd.ttf", "C:/Windows/Fonts/arialbd.ttf"]:
            try: return ImageFont.truetype(p, sz)
            except: pass
        return self.gfont(sz)

    def draw_shadow(self, draw, pos, text, font, fill='white', shadow_color='black', offset=3):
        x, y = pos
        for dx in range(-offset, offset+1):
            for dy in range(-offset, offset+1):
                if dx != 0 or dy != 0:
                    draw.text((x+dx, y+dy), text, fill=shadow_color, font=font)
        draw.text((x, y), text, fill=fill, font=font)

    def reshape(self, t):
        return get_display(arabic_reshaper.reshape(t))

    def dshadow(self, d, pos, t, f, fill='white', s='black', o=3):
        x, y = pos
        for dx in range(-o, o+1):
            for dy in range(-o, o+1):
                if dx != 0 or dy != 0:
                    d.text((x+dx, y+dy), t, fill=s, font=f)
        d.text((x, y), t, fill=fill, font=f)

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

            log(f"build_page: i={i} per_image_settings={list(self.per_image_settings.keys())}")

            # Load per-image settings if available
            if i in self.per_image_settings:
                s = self.per_image_settings[i]
                positions = s.get('positions') or self.custom_positions
                tw_map = s.get('text_width', self.custom_text_width)
                talign = s.get('text_align', self.text_align)
                tpos = s.get('text_positions', self.text_positions)
                num_sz = s.get('number_size', self.number_size)
                title_sz = s.get('title_size', self.title_size)
                summ_sz = s.get('summary_size', self.summary_size)
                log(f"  Using per-image settings for i={i}")
                log(f"  full s={s}")
            else:
                positions = self.custom_positions
                tw_map = self.custom_text_width
                talign = self.text_align
                tpos = self.text_positions
                num_sz = self.number_size
                title_sz = self.title_size
                summ_sz = self.summary_size
                log(f"  Using default settings for i={i}")

            # Number
            nt = str(self.start_number+i)
            nf = self.gbold(num_sz)
            if positions and 'number' in positions:
                sx, sy = cw/590, ch/830
                nx = x+int(positions['number']['x']*sx)
                ny = y+int(positions['number']['y']*sy)
            else:
                bbox = draw.textbbox((0,0),nt,font=nf)
                nw = bbox[2]-bbox[0]
                nx = x+(cw-nw-20); ny = y+15
            bbox = draw.textbbox((0,0),nt,font=nf)
            nw = bbox[2]-bbox[0]
            log(f"  NUMBER i={i}: nx={nx} ny={ny} x={x} y={y} cw={cw} ch={ch}")
            draw.rounded_rectangle([nx-15,ny-10,nx+nw+15,ny+15], radius=10, fill=(200,30,30))
            self.dshadow(draw,(nx,ny),nt,nf,'white','darkred',2)

            # Title
            if item.get('show_title') and item.get('title'):
                tf = self.gbold(title_sz)
                tw = tw_map.get('title', cw-60)
                lines = self.wrap_rtl(item['title'], tf, tw, draw)
                p2 = tpos['title']
                tx = x+int(p2['x'])
                ty = y+int(p2['y'])
                ta = talign.get('title', 'right')
                for j, line in enumerate(lines):
                    line = self.reshape(line)
                    lw = draw.textbbox((0,0),line,font=tf)[2]
                    if ta == 'right': lx = tx+tw-lw
                    elif ta == 'center': lx = tx+(tw-lw)//2
                    else: lx = tx
                    self.dshadow(draw, (lx, ty+j*(title_sz+5)), line, tf, fill='red', s='white', o=3)

            # Summary
            if item.get('summary'):
                sf = self.gfont(summ_sz)
                sw = tw_map.get('summary', cw-60)
                lines = self.wrap_rtl(item['summary'], sf, sw, draw)
                p3 = tpos['summary']
                sxx = x+int(p3['x'])
                syy = y+int(p3['y'])
                sa = talign.get('summary', 'right')
                log(f"  SUMMARY i={i}: p3={p3} sxx={sxx} syy={syy} y+ch={y+ch}")
                for j, line in enumerate(lines):
                    line = self.reshape(line)
                    lw = draw.textbbox((0,0),line,font=sf)[2]
                    if sa == 'right': lx = sxx+sw-lw
                    elif sa == 'center': lx = sxx+(sw-lw)//2
                    else: lx = sxx
                    ly = syy+j*(summ_sz+3)
                    if ly < y + ch - 10:
                        self.dshadow(draw, (lx, ly), line, sf, fill='white', s='black', o=3)

            draw.rectangle([x,y,x+cw-1,y+ch-1], outline=(50,50,50), width=2)
        return page

    def fit_text(self, text, max_w, max_h, draw, bold=True):
        words = text.split()
        reshaped_words = [self.reshape(w) for w in words]
        for sz in range(80, 15, -2):
            f = self.gbold(sz) if bold else self.gfont(sz)
            lines, cur = [], ""
            for rw in reshaped_words:
                test = rw + " " + cur if cur else rw
                if draw.textbbox((0,0), test, font=f)[2] <= max_w:
                    cur = test
                else:
                    if cur: lines.append(cur)
                    cur = rw
            if cur: lines.append(cur)
            total_h = len(lines) * (sz + 6)
            if total_h <= max_h:
                return f, lines, sz
        f = self.gbold(15) if bold else self.gfont(15)
        lines, cur = [], ""
        for rw in reshaped_words:
            test = rw + " " + cur if cur else rw
            if draw.textbbox((0,0), test, font=f)[2] <= max_w:
                cur = test
            else:
                if cur: lines.append(cur)
                cur = rw
        if cur: lines.append(cur)
        return f, lines, 15

    def draw_gradient_rect(self, draw, x1, y1, x2, y2, color1, color2, radius=0):
        for i in range(y2 - y1):
            ratio = i / (y2 - y1)
            r = int(color1[0] * (1 - ratio) + color2[0] * ratio)
            g = int(color1[1] * (1 - ratio) + color2[1] * ratio)
            b = int(color1[2] * (1 - ratio) + color2[2] * ratio)
            draw.line([(x1, y1 + i), (x2, y1 + i)], fill=(r, g, b))

    def build_text_catalog(self):
        W, H = 2480, 3508
        M = 25
        cols = 3
        rows = 3
        cell_w = (W - (cols+1)*M) // cols
        cell_h = (H - (rows+1)*M) // rows

        page = Image.new('RGB', (W, H), '#f8f9fa')
        draw = ImageDraw.Draw(page)

        for i, item in enumerate(self.items[:9]):
            col = i % cols
            row = i // cols
            x = M + col * (cell_w + M)
            y = M + row * (cell_h + M)

            self.draw_gradient_rect(draw, x, y, x+cell_w, y+cell_h, (255,255,255), (245,245,245))
            draw.rounded_rectangle([x, y, x+cell_w, y+cell_h], radius=12, fill=None, outline='#e0e0e0', width=2)

            num = self.start_number + i
            nf = self.gbold(70)
            num_text = str(num)
            bbox = draw.textbbox((0,0), num_text, font=nf)
            nw = bbox[2] - bbox[0]
            num_x = x + (cell_w - nw) // 2
            draw.rounded_rectangle([num_x - 25, y + 20, num_x + nw + 25, y + 95], radius=15, fill='#d32f2f')
            for dx in range(-2, 3):
                for dy in range(-2, 3):
                    if dx != 0 or dy != 0:
                        draw.text((num_x+dx, y+18+dy), num_text, fill='#b71c1c', font=nf)
            draw.text((num_x, y + 18), num_text, fill='white', font=nf)

            current_y = y + 110

            title = item.get('title', '')
            if title:
                tf, tlines, tsz = self.fit_text(title, cell_w - 50, int(cell_h * 0.2), draw, bold=True)
                for j, line in enumerate(tlines):
                    bbox = draw.textbbox((0,0), line, font=tf)
                    lw = bbox[2] - bbox[0]
                    tx = x + (cell_w - lw) // 2
                    ty = current_y + j*(tsz+8)
                    for dx in range(-1, 2):
                        for dy in range(-1, 2):
                            if dx != 0 or dy != 0:
                                draw.text((tx+dx, ty+dy), line, fill='#e8d5d5', font=tf)
                    draw.text((tx, ty), line, fill='#b71c1c', font=tf)
                current_y += len(tlines) * (tsz + 8) + 10

            line_y = current_y
            draw.line([(x + 30, line_y), (x + cell_w - 30, line_y)], fill='#e0e0e0', width=2)
            current_y += 15

            genre = item.get('genre', '')
            year = item.get('year', '')
            if genre or year:
                gf = self.gbold(24)
                info = f"{genre} | {year}" if genre and year else genre or year
                info = self.reshape(info)
                bbox = draw.textbbox((0,0), info, font=gf)
                iw = bbox[2] - bbox[0]
                draw.text((x + (cell_w - iw) // 2, current_y), info, fill='#000000', font=gf)
                current_y += 45

            summary = item.get('summary', '')
            if summary:
                sf, slines, ssz = self.fit_text(summary, cell_w - 40, y + cell_h - current_y - 20, draw, bold=False)
                for j, line in enumerate(slines):
                    bbox = draw.textbbox((0,0), line, font=sf)
                    lw = bbox[2] - bbox[0]
                    tx = x + (cell_w - lw) // 2
                    ty = current_y + j*(ssz+6)
                    for dx in range(-1, 2):
                        for dy in range(-1, 2):
                            if dx != 0 or dy != 0:
                                draw.text((tx+dx, ty+dy), line, fill='#e8e8e8', font=sf)
                    draw.text((tx, ty), line, fill='#333333', font=sf)

        return page

    def preview_text_catalog(self):
        try:
            if not self.items:
                return QMessageBox.warning(self, "Warning", "Empty!")
            self._catalog_page = self.build_text_catalog()
            pg = self._catalog_page
            win = QDialog(self)
            win.setWindowTitle("Text Catalog Preview")
            lay = QVBoxLayout(win)
            lbl = QLabel()
            ph = 800
            pw = int(ph * 2480 / 3508)
            resized = pg.copy()
            resized.thumbnail((pw, ph), Image.Resampling.LANCZOS)
            pm = pil_to_qpixmap(resized)
            if pm:
                lbl.setPixmap(pm)
            lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
            lay.addWidget(lbl)
            bf = QHBoxLayout()

            def save_png():
                self._save(self._catalog_page, 'png')

            def save_pdf():
                self._save(self._catalog_page, 'pdf')

            b1 = QPushButton("PNG"); b1.clicked.connect(save_png); bf.addWidget(b1)
            b2 = QPushButton("PDF"); b2.clicked.connect(save_pdf); bf.addWidget(b2)
            b3 = QPushButton("Close"); b3.clicked.connect(win.close); bf.addWidget(b3)
            lay.addLayout(bf)
            win.exec()
        except Exception as e:
            QMessageBox.critical(self, "Error", str(e))

    def build_9poster(self):
        W, H = 2480, 3508
        M = 30
        cols = 3
        rows = 3
        cell_w = (W - (cols+1)*M) // cols
        cell_h = (H - (rows+1)*M) // rows

        page = Image.new('RGB', (W, H), '#f8f9fa')
        draw = ImageDraw.Draw(page)

        for i, item in enumerate(self.items[:9]):
            col = i % cols
            row = i // cols
            x = M + col * (cell_w + M)
            y = M + row * (cell_h + M)

            self.draw_gradient_rect(draw, x, y, x+cell_w, y+cell_h, (255,255,255), (240,240,240))
            draw.rounded_rectangle([x, y, x+cell_w, y+cell_h], radius=15, fill=None, outline='#d0d0d0', width=3)

            try:
                img = item['image'].copy().resize((cell_w, cell_h), Image.Resampling.LANCZOS)
                img = ImageEnhance.Brightness(img).enhance(0.8)
                page.paste(img, (x, y))
                ov = Image.new('RGBA', (cell_w, cell_h), (0,0,0,0))
                od = ImageDraw.Draw(ov)
                for gy in range(cell_h//3):
                    od.line([(0,cell_h-gy),(cell_w,cell_h-gy)], fill=(0,0,0,int(150*(1-gy/(cell_h//3)))))
                page.paste(Image.alpha_composite(page.crop((x,y,x+cell_w,y+cell_h)).convert('RGBA'), ov).convert('RGB'), (x,y))
            except Exception as e:
                print(f"Image error: {e}")

            num = self.start_number + i
            nf = self.gbold(120)
            num_text = str(num)
            bbox = draw.textbbox((0,0), num_text, font=nf)
            nw = bbox[2] - bbox[0]
            num_x = x + (cell_w - nw) // 2
            draw.rounded_rectangle([num_x - 30, y + 30, num_x + nw + 30, y + 140], radius=20, fill='#d32f2f')
            for dx in range(-3, 4):
                for dy in range(-3, 4):
                    if dx != 0 or dy != 0:
                        draw.text((num_x+dx, y+28+dy), num_text, fill='#8b0000', font=nf)
            draw.text((num_x, y + 28), num_text, fill='white', font=nf)

            title = item.get('title', '')
            if title:
                tf, tlines, tsz = self.fit_text(title, cell_w - 80, cell_h - 200, draw, bold=True)
                title_y = y + 160
                for j, line in enumerate(tlines):
                    bbox = draw.textbbox((0,0), line, font=tf)
                    lw = bbox[2] - bbox[0]
                    tx = x + (cell_w - lw) // 2
                    ty = title_y + j*(tsz+10)
                    for dx in range(-2, 3):
                        for dy in range(-2, 3):
                            if dx != 0 or dy != 0:
                                draw.text((tx+dx, ty+dy), line, fill='#f5f5f5', font=tf)
                    draw.text((tx, ty), line, fill='#c62828', font=tf)

        self._last_page = page
        return page

    def preview_9poster(self):
        try:
            if not self.items:
                return QMessageBox.warning(self, "Warning", "Empty!")

            self._poster_page = self.build_9poster()

            if not hasattr(self, 'poster_positions_all'):
                self.poster_positions_all = {}
            if not hasattr(self, 'poster_idx'):
                self.poster_idx = 0
            if self.poster_idx not in self.poster_positions_all:
                self.poster_positions_all[self.poster_idx] = {'number': {'x': 400, 'y': 50}, 'title': {'x': 30, 'y': 250}}

            win = QDialog(self)
            win.setWindowTitle("9 Poster - Drag to Move")
            win.setMinimumSize(720, 960)
            lay = QVBoxLayout(win)

            info = QLabel("Circle = Move | Square = Resize")
            info.setStyleSheet("color:#00d4aa; font-size:11px;")
            info.setAlignment(Qt.AlignmentFlag.AlignCenter)
            lay.addWidget(info)

            nav = QHBoxLayout()
            btn_prev = QPushButton("<")
            btn_prev.setFixedWidth(50)
            lbl = QLabel(f"Image 1 / {len(self.items)}")
            lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
            lbl.setStyleSheet("font-size:13px; font-weight:bold;")
            btn_next = QPushButton(">")
            btn_next.setFixedWidth(50)
            nav.addWidget(btn_prev)
            nav.addWidget(lbl)
            nav.addWidget(btn_next)
            lay.addLayout(nav)

            canvas = EditorCanvas()
            lay.addWidget(canvas, alignment=Qt.AlignmentFlag.AlignCenter)

            self.poster_canvas_ref = canvas
            self.poster_idx = 0
            self.poster_win = win

            def redraw_poster():
                try:
                    if not self.items:
                        return
                    item = self.items[self.poster_idx]
                    cw, ch = 590, 830
                    img = item['image'].copy().resize((cw, ch), Image.Resampling.LANCZOS)
                    img = ImageEnhance.Brightness(img).enhance(0.7)
                    ov = Image.new('RGBA', (cw, ch), (0,0,0,0))
                    od = ImageDraw.Draw(ov)
                    for gy in range(ch//3):
                        od.line([(0,ch-gy),(cw,ch-gy)], fill=(0,0,0,int(180*(1-gy/(ch//3)))))
                    base = Image.alpha_composite(img.copy().convert('RGBA'), ov).convert('RGB')
                    draw = ImageDraw.Draw(base)

                    p = self.poster_positions_all[self.poster_idx]
                    nt = str(self.start_number + self.poster_idx)
                    nf = self.gbold(self.number_size)
                    px, py = int(p['number']['x']), int(p['number']['y'])
                    bbox = draw.textbbox((0,0), nt, font=nf)
                    nw = bbox[2]-bbox[0]
                    draw.rounded_rectangle([px-15, py-10, px+nw+15, py+15], radius=10, fill=(200,30,30))
                    draw.text((px, py), nt, fill='white', font=nf)

                    if item.get('show_title') and item.get('title'):
                        tf = self.gbold(self.title_size)
                        p2 = self.poster_positions_all[self.poster_idx]['title']
                        px2, py2 = int(p2['x']), int(p2['y'])
                        tw = self.custom_text_width.get('title', cw-60)
                        lines = self.wrap_rtl(item['title'], tf, tw, draw)
                        for j, line in enumerate(lines):
                            line = self.reshape(line)
                            lw = draw.textbbox((0,0),line,font=tf)[2]
                            draw.text((px2+(tw-lw)//2, py2+j*(self.title_size+5)), line, fill='white', font=tf)

                    self.poster_base = base
                    resize_t = {}
                    sizes = {'number':self.number_size,'title':self.title_size,'summary':self.summary_size}
                    y_pos = {'number':60,'title':380,'summary':520}
                    colors_d = {'number':'#ff6d00','title':'#6c5ce7','summary':'#00cec9'}
                    for nm in ['number','title']:
                        ry = y_pos[nm]
                        resize_t[nm] = {'x':557,'y':ry,'sz':sizes[nm]}
                    canvas.set_pil_image(base)
                    canvas.move_targets = self.poster_positions_all[self.poster_idx]
                    canvas.resize_targets = resize_t

                    # Build text zones for title
                    text_zones = {}
                    if item.get('show_title') and item.get('title'):
                        tf = self.gbold(self.title_size)
                        tw = self.custom_text_width.get('title', cw-60)
                        tlines = self.wrap_rtl(item['title'], tf, tw, draw)
                        p2 = self.poster_positions_all[self.poster_idx]['title']
                        th = len(tlines) * (self.title_size + 5)
                        text_zones['title'] = {'x': int(p2['x']), 'y': int(p2['y']), 'w': tw, 'h': th, 'sz': self.title_size}
                    canvas.text_zones = text_zones
                except Exception as e:
                    print(f"Redraw error: {e}")

            def on_change(mode, name, val1, val2=None):
                try:
                    if mode == 'move':
                        item = self.items[self.poster_idx]
                        cw, ch = 590, 830
                        cx = (590 - cw) // 2
                        cy = (830 - ch) // 2
                        rel_x = max(0, min(cw - 50, val1 - cx))
                        rel_y = max(0, min(ch - 50, val2 - cy))
                        self.poster_positions_all[self.poster_idx][name] = {'x': rel_x, 'y': rel_y}
                        print(f"Saved: idx={self.poster_idx} name={name} rel=({rel_x},{rel_y}) abs=({val1},{val2})")
                    elif mode == 'resize':
                        if name == 'number':
                            self.number_size = max(30, min(200, val1))
                        elif name == 'title':
                            self.title_size = max(16, min(80, val1))
                    safe_redraw()
                except Exception as e:
                    print(f"on_change error: {e}")

            canvas.on_change = on_change
            canvas.move_targets = self.poster_positions_all[self.poster_idx]

            def safe_redraw():
                try:
                    if win.isVisible():
                        redraw_poster()
                except:
                    pass

            def next_img():
                if self.poster_idx < len(self.items)-1:
                    self.poster_idx += 1
                    if self.poster_idx not in self.poster_positions_all:
                        self.poster_positions_all[self.poster_idx] = {'number': {'x': 400, 'y': 50}, 'title': {'x': 30, 'y': 250}}
                    canvas.move_targets = self.poster_positions_all[self.poster_idx]
                    lbl.setText(f"Image {self.poster_idx+1} / {len(self.items)}")
                    safe_redraw()

            def prev_img():
                if self.poster_idx > 0:
                    self.poster_idx -= 1
                    if self.poster_idx not in self.poster_positions_all:
                        self.poster_positions_all[self.poster_idx] = {'number': {'x': 400, 'y': 50}, 'title': {'x': 30, 'y': 250}}
                    canvas.move_targets = self.poster_positions_all[self.poster_idx]
                    lbl.setText(f"Image {self.poster_idx+1} / {len(self.items)}")
                    safe_redraw()

            btn_next.clicked.connect(next_img)
            btn_prev.clicked.connect(prev_img)

            sf = QHBoxLayout()
            sf.addWidget(QLabel("Number:"))
            bd1 = QPushButton("-"); bd1.setFixedWidth(35); bd1.setStyleSheet("background:#e17055;")
            bd1.clicked.connect(lambda: [self.sp_num.setValue(max(30, self.sp_num.value()-2)), redraw_poster()])
            sf.addWidget(bd1)
            sf.addWidget(self.sp_num)
            bi1 = QPushButton("+"); bi1.setFixedWidth(35); bi1.setStyleSheet("background:#00b894;")
            bi1.clicked.connect(lambda: [self.sp_num.setValue(min(200, self.sp_num.value()+2)), redraw_poster()])
            sf.addWidget(bi1)
            sf.addWidget(QLabel("Title:"))
            bd2 = QPushButton("-"); bd2.setFixedWidth(35); bd2.setStyleSheet("background:#e17055;")
            bd2.clicked.connect(lambda: [self.sp_title.setValue(max(16, self.sp_title.value()-2)), redraw_poster()])
            sf.addWidget(bd2)
            sf.addWidget(self.sp_title)
            bi2 = QPushButton("+"); bi2.setFixedWidth(35); bi2.setStyleSheet("background:#00b894;")
            bi2.clicked.connect(lambda: [self.sp_title.setValue(min(80, self.sp_title.value()+2)), redraw_poster()])
            sf.addWidget(bi2)
            lay.addLayout(sf)

            bf = QHBoxLayout()
            b0 = QPushButton("Save"); b0.setStyleSheet("background:#00b894;")
            b0.clicked.connect(lambda: [self._save_poster_settings(), QMessageBox.information(win, "Done", "Settings saved!")])
            bf.addWidget(b0)
            b1 = QPushButton("PNG"); b1.clicked.connect(lambda: self._save(self._poster_page, 'png')); bf.addWidget(b1)
            b2 = QPushButton("PDF"); b2.clicked.connect(lambda: self._save(self._poster_page, 'pdf')); bf.addWidget(b2)
            b3 = QPushButton("Close"); b3.clicked.connect(win.close); bf.addWidget(b3)
            lay.addLayout(bf)

            redraw_poster()
            win.exec()
        except Exception as e:
            QMessageBox.critical(self, "Error", str(e))

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

    def _save_poster_settings(self):
        self._last_page = self.build_9poster_from_settings()

    def build_9poster_from_settings(self):
        W, H = 2480, 3508
        M = 30
        cols = 3
        rows = 3
        cell_w = (W - (cols+1)*M) // cols
        cell_h = (H - (rows+1)*M) // rows

        page = Image.new('RGB', (W, H), '#f8f9fa')
        draw = ImageDraw.Draw(page)

        for i, item in enumerate(self.items[:9]):
            col = i % cols
            row = i // cols
            x = M + col * (cell_w + M)
            y = M + row * (cell_h + M)

            self.draw_gradient_rect(draw, x, y, x+cell_w, y+cell_h, (255,255,255), (240,240,240))
            draw.rounded_rectangle([x, y, x+cell_w, y+cell_h], radius=15, fill=None, outline='#d0d0d0', width=3)

            try:
                img = item['image'].copy().resize((cell_w, cell_h), Image.Resampling.LANCZOS)
                img = ImageEnhance.Brightness(img).enhance(0.8)
                page.paste(img, (x, y))
                ov = Image.new('RGBA', (cell_w, cell_h), (0,0,0,0))
                od = ImageDraw.Draw(ov)
                for gy in range(cell_h//3):
                    od.line([(0,cell_h-gy),(cell_w,cell_h-gy)], fill=(0,0,0,int(150*(1-gy/(cell_h//3)))))
                page.paste(Image.alpha_composite(page.crop((x,y,x+cell_w,y+cell_h)).convert('RGBA'), ov).convert('RGB'), (x,y))
            except Exception as e:
                print(f"Image error: {e}")

            default_pos = {'number': {'x': cell_w//2 - 50, 'y': 30}, 'title': {'x': cell_w//2 - 100, 'y': 200}}
            p = self.poster_positions_all.get(i, default_pos)

            sx = cell_w / 590.0
            sy = cell_h / 830.0

            num = self.start_number + i
            nf = self.gbold(self.number_size)
            num_text = str(num)
            px = x + int(p['number']['x'] * sx)
            py = y + int(p['number']['y'] * sy)
            bbox = draw.textbbox((0,0), num_text, font=nf)
            nw = bbox[2] - bbox[0]
            draw.rounded_rectangle([px - 30, py - 10, px + nw + 30, py + 100], radius=20, fill='#d32f2f')
            for dx in range(-3, 4):
                for dy in range(-3, 4):
                    if dx != 0 or dy != 0:
                        draw.text((px+dx, py+dy), num_text, fill='#8b0000', font=nf)
            draw.text((px, py), num_text, fill='white', font=nf)

            title = item.get('title', '')
            if item.get('show_title') and title:
                tf, tlines, tsz = self.fit_text(title, cell_w - 80, cell_h - 200, draw, bold=True)
                px2 = x + int(p['title']['x'] * sx)
                py2 = y + int(p['title']['y'] * sy)
                for j, line in enumerate(tlines):
                    bbox = draw.textbbox((0,0), line, font=tf)
                    lw = bbox[2] - bbox[0]
                    tx = px2 + ((cell_w - 80) - lw) // 2
                    ty = py2 + j*(tsz+10)
                    for dx in range(-2, 3):
                        for dy in range(-2, 3):
                            if dx != 0 or dy != 0:
                                draw.text((tx+dx, ty+dy), line, fill='#f5f5f5', font=tf)
                    draw.text((tx, ty), line, fill='#c62828', font=tf)

        self._last_page = page
        return page

    def _save(self, page, fmt):
        if fmt == 'pdf':
            p, _ = QFileDialog.getSaveFileName(self, "Save", "", "PDF Files (*.pdf)")
        else:
            p, _ = QFileDialog.getSaveFileName(self, "Save", "", "PNG Files (*.png)")
        if p:
            try:
                if fmt == 'pdf':
                    page.save(p, "PDF", resolution=300)
                else:
                    page.save(p, quality=95)
                QMessageBox.information(self, "Done", "Saved!")
            except Exception as e:
                QMessageBox.critical(self, "Error", str(e))

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

                    # Load per-image settings
                    if idx in self.per_image_settings:
                        s = self.per_image_settings[idx]
                        positions = s.get('positions', self.custom_positions) or self.custom_positions
                        tw_map = s.get('text_width', self.custom_text_width)
                        talign = s.get('text_align', self.text_align)
                        tpos = s.get('text_positions', self.text_positions)
                        num_sz = s.get('number_size', self.number_size)
                        title_sz = s.get('title_size', self.title_size)
                        summ_sz = s.get('summary_size', self.summary_size)
                    else:
                        positions = self.custom_positions
                        tw_map = self.custom_text_width
                        talign = self.text_align
                        tpos = self.text_positions
                        num_sz = self.number_size
                        title_sz = self.title_size
                        summ_sz = self.summary_size

                    sizes = {'number': num_sz, 'title': title_sz, 'summary': summ_sz}

                    # Number
                    nt = str(self.start_number + idx)
                    nf = self.gbold(num_sz)
                    p = positions['number']
                    px, py = int(p['x']), int(p['y'])
                    bbox = draw.textbbox((0,0), nt, font=nf)
                    nw, nh = bbox[2]-bbox[0], bbox[3]-bbox[1]
                    draw.rounded_rectangle([px-15,py-10,px+nw+15,py+nh+10], radius=10, fill=(200,30,30))
                    draw.text((px,py), nt, fill='white', font=nf)

                    # Title
                    if item.get('show_title') and item.get('title'):
                        tf = self.gbold(title_sz)
                        p2 = tpos['title']
                        px2, py2 = int(p2['x']), int(p2['y'])
                        tw = tw_map.get('title', cw-60)
                        lines = self.wrap_rtl(item['title'], tf, tw, draw)
                        ta = talign.get('title', 'right')
                        for j, line in enumerate(lines):
                            line = self.reshape(line)
                            lw = draw.textbbox((0,0),line,font=tf)[2]
                            if ta == 'right':
                                lx = px2 + tw - lw
                            elif ta == 'center':
                                lx = px2 + (tw - lw) // 2
                            else:
                                lx = px2
                            self.dshadow(draw, (lx, py2+j*(title_sz+5)), line, tf, fill='red', s='white', o=3)

                    # Summary
                    if item.get('summary'):
                        sf = self.gfont(summ_sz)
                        p3 = tpos['summary']
                        px3, py3 = int(p3['x']), int(p3['y'])
                        sw = tw_map.get('summary', cw-60)
                        lines = self.wrap_rtl(item['summary'], sf, sw, draw)
                        sa = talign.get('summary', 'right')
                        for j, line in enumerate(lines):
                            line = self.reshape(line)
                            lw = draw.textbbox((0,0),line,font=sf)[2]
                            if sa == 'right':
                                lx = px3 + sw - lw
                            elif sa == 'center':
                                lx = px3 + (sw - lw) // 2
                            else:
                                lx = px3
                            self.dshadow(draw, (lx, py3+j*(self.summary_size+3)), line, sf, fill='white', s='black', o=3)

                    # Move handles
                    for nm, ps in positions.items():
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
                        tf = self.gbold(title_sz)
                        tw = max(tw_map.get('title', cw-60), 200)
                        tlines = self.wrap_rtl(item['title'], tf, tw, draw)
                        p2 = tpos['title']
                        th = max(len(tlines) * (title_sz + 5), 60)
                        text_zones['title'] = {'x': int(p2['x']), 'y': int(p2['y']), 'w': tw, 'h': th, 'sz': title_sz}
                    if item.get('summary'):
                        sf = self.gfont(summ_sz)
                        sw = max(tw_map.get('summary', cw-60), 200)
                        slines = self.wrap_rtl(item['summary'], sf, sw, draw)
                        p3 = tpos['summary']
                        sh = max(len(slines) * (summ_sz + 3), 60)
                        text_zones['summary'] = {'x': int(p3['x']), 'y': int(p3['y']), 'w': sw, 'h': sh, 'sz': summ_sz}

                    canvas_overlay.set_data(positions.copy(), resize_t, text_zones)

                    log(f"  drawing image {base.size}")
                    pm = pil_to_qpixmap(base)
                    if pm:
                        canvas_lbl.setPixmap(pm)
                        log("  pixmap set on canvas_lbl OK")
                    else:
                        log("  ERROR: pixmap is None!")

                except Exception as e:
                    log(f"  draw_in_editor EXCEPTION: {e}")
                    log_err(e)

            def on_canvas_change(mode, name, val1, val2=None):
                try:
                    idx = self.editor_idx
                    log(f"  on_canvas_change: mode={mode} name={name} idx={idx}")
                    if idx not in self.per_image_settings:
                        self.per_image_settings[idx] = {
                            'positions': self.custom_positions.copy() if self.custom_positions else None,
                            'text_width': self.custom_text_width.copy(),
                            'text_align': self.text_align.copy(),
                            'text_positions': self.text_positions.copy(),
                            'number_size': self.number_size,
                            'title_size': self.title_size,
                            'summary_size': self.summary_size
                        }
                    s = self.per_image_settings[idx]

                    if mode == 'move':
                        if name in ('title', 'summary'):
                            if not s.get('text_positions'):
                                s['text_positions'] = self.text_positions.copy()
                            s['text_positions'][name] = {'x': val1, 'y': val2}
                        else:
                            if not s.get('positions'):
                                s['positions'] = self.custom_positions.copy() if self.custom_positions else {'number': {'x': 480, 'y': 20}}
                            s['positions'][name] = {'x': val1, 'y': val2}
                    elif mode == 'resize':
                        if name == 'number':
                            s['number_size'] = max(30, min(200, val1))
                            self.sp_num.setValue(s['number_size'])
                        elif name == 'title':
                            s['title_size'] = max(16, min(80, val1))
                            self.sp_title.setValue(s['title_size'])
                        elif name == 'summary':
                            s['summary_size'] = max(10, min(50, val1))
                            self.sp_summ.setValue(s['summary_size'])
                    elif mode == 'text_resize':
                        if name == 'title':
                            if not s.get('text_width'):
                                s['text_width'] = self.custom_text_width.copy()
                            s['text_width']['title'] = max(100, min(570, val1))
                            if val2 is not None:
                                s['title_size'] = max(16, min(80, val2))
                                self.sp_title.setValue(s['title_size'])
                        elif name == 'summary':
                            if not s.get('text_width'):
                                s['text_width'] = self.custom_text_width.copy()
                            s['text_width']['summary'] = max(100, min(570, val1))
                            if val2 is not None:
                                s['summary_size'] = max(10, min(50, val2))
                                self.sp_summ.setValue(s['summary_size'])
                    elif mode == 'text_move':
                        log(f"  text_move: name={name} val1={val1} val2={val2}")
                        if not s.get('text_positions'):
                            s['text_positions'] = self.text_positions.copy()
                        s['text_positions'][name] = {'x': val1, 'y': val2}
                        log(f"  saved text_positions={s['text_positions']}")
                    draw_in_editor()
                except Exception as e:
                    log_err(e)

            canvas_overlay.on_change = on_canvas_change

            def update_align_btns(btns, key, active_align):
                color = '#6c5ce7' if key == 'title' else '#00cec9'
                for btn, align in btns:
                    btn.setStyleSheet(f"background:{color};" if align == active_align else "background:#333;")

            def load_settings_for_image(idx):
                if idx in self.per_image_settings:
                    s = self.per_image_settings[idx]
                    if 'positions' in s and s['positions']:
                        self.custom_positions = s['positions'].copy()
                    if 'text_width' in s:
                        self.custom_text_width = s['text_width'].copy()
                    if 'text_align' in s:
                        self.text_align = s['text_align'].copy()
                    if 'text_positions' in s:
                        self.text_positions = s['text_positions'].copy()
                    if 'number_size' in s:
                        self.number_size = s['number_size']
                    if 'title_size' in s:
                        self.title_size = s['title_size']
                    if 'summary_size' in s:
                        self.summary_size = s['summary_size']
                    try:
                        self.sp_num.setValue(self.number_size)
                        self.sp_title.setValue(self.title_size)
                        self.sp_summ.setValue(self.summary_size)
                    except RuntimeError:
                        pass

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
            def on_spinbox_change():
                idx = self.editor_idx
                if idx not in self.per_image_settings:
                    self.per_image_settings[idx] = {}
                s = self.per_image_settings[idx]
                s['number_size'] = self.sp_num.value()
                s['title_size'] = self.sp_title.value()
                s['summary_size'] = self.sp_summ.value()
                self.number_size = s['number_size']
                self.title_size = s['title_size']
                self.summary_size = s['summary_size']
                draw_in_editor()

            for label, attr, mn, mx in [("Number","sp_num",30,200),("Title","sp_title",16,80),("Summary","sp_summ",10,50)]:
                sf.addWidget(QLabel(f"{label}:"))
                bd = QPushButton("-"); bd.setFixedWidth(35); bd.setStyleSheet("background:#e17055;")
                sp = getattr(self, attr)
                sp.valueChanged.connect(on_spinbox_change)
                bd.clicked.connect(lambda c, sp=sp, v=mn: sp.setValue(max(v, sp.value()-2)))
                sf.addWidget(bd); sf.addWidget(sp)
                bi = QPushButton("+"); bi.setFixedWidth(35); bi.setStyleSheet("background:#00b894;")
                bi.clicked.connect(lambda c, sp=sp, v=mx: sp.setValue(min(v, sp.value()+2)))
                sf.addWidget(bi)
            lay.addLayout(sf)

            af = QHBoxLayout()
            af.addWidget(QLabel("Title Align:"))
            title_align_btns = []
            for align, label in [("right", "R"), ("center", "C"), ("left", "L")]:
                btn = QPushButton(label)
                btn.setFixedWidth(35)
                btn.setStyleSheet("background:#6c5ce7;" if self.text_align.get('title') == align else "background:#333;")
                btn.clicked.connect(lambda c, a=align, b=btn: [self.text_align.__setitem__('title', a), update_align_btns(title_align_btns, 'title', a), draw_in_editor()])
                title_align_btns.append((btn, align))
                af.addWidget(btn)
            af.addSpacing(20)
            af.addWidget(QLabel("Summary Align:"))
            summary_align_btns = []
            for align, label in [("right", "R"), ("center", "C"), ("left", "L")]:
                btn = QPushButton(label)
                btn.setFixedWidth(35)
                btn.setStyleSheet("background:#00cec9;" if self.text_align.get('summary') == align else "background:#333;")
                btn.clicked.connect(lambda c, a=align, b=btn: [self.text_align.__setitem__('summary', a), update_align_btns(summary_align_btns, 'summary', a), draw_in_editor()])
                summary_align_btns.append((btn, align))
                af.addWidget(btn)
            lay.addLayout(af)

            bc = QPushButton("Save"); bc.setStyleSheet("background:#00b894;")
            bc.clicked.connect(lambda: QMessageBox.information(dlg, "Done", "Saved!"))
            lay.addWidget(bc)

            bcl = QPushButton("Close"); bcl.setStyleSheet("background:#e17055;")
            def close_editor():
                for sp_attr in ['sp_num', 'sp_title', 'sp_summ']:
                    try:
                        sp = getattr(self, sp_attr)
                        sp.valueChanged.disconnect()
                    except:
                        pass
                dlg.close()
            bcl.clicked.connect(close_editor)
            lay.addWidget(bcl)

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
