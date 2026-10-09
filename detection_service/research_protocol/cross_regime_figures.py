"""Deterministic dependency-free SVG figures from frozen cross-regime figure data.

Pure string rendering: no plotting backend, fonts as text, fixed numeric
formatting, so identical figure data always yields identical bytes.
"""
from html import escape

SURFACE, TEXT, TEXT2, MUTED = '#fcfcfb', '#0b0b0b', '#52514e', '#8a8984'
GRID, AXIS = '#e6e5e0', '#b9b8b2'
SERIES = {'ds_v2': '#2a78d6', 'dm_b_v1': '#eb6834', 'dg_v1': '#1baf7a'}
SINGLE = '#2a78d6'
POSITIVE, NEGATIVE = '#e34948', '#2a78d6'
SEQUENTIAL = ('#f0efec', '#cde2fb', '#9ec5f4', '#6da7ec', '#3987e5', '#256abf', '#184f95', '#0d366b')
FONT = 'DejaVu Sans, Helvetica, Arial, sans-serif'


def n(value):
    return f'{value:.2f}'


class Svg:
    def __init__(self, width, height, title, description):
        self.width, self.height, self.parts = width, height, []
        self.title, self.description = title, description

    def text(self, x, y, value, size=10, anchor='start', color=TEXT, weight='normal'):
        for offset, line in enumerate(str(value).split('\n')):
            self.parts.append(f'<text x="{n(x)}" y="{n(y + offset * size * 1.2)}" font-size="{size}" '
                              f'text-anchor="{anchor}" fill="{color}" font-weight="{weight}">{escape(line)}</text>')

    def rect(self, x, y, width, height, fill, rx=0.0, title=None):
        tip = f'<title>{escape(title)}</title>' if title else ''
        self.parts.append(f'<rect x="{n(x)}" y="{n(y)}" width="{n(max(width, 0))}" height="{n(max(height, 0))}" '
                          f'rx="{n(rx)}" fill="{fill}">{tip}</rect>')

    def line(self, x1, y1, x2, y2, color=AXIS, width=1.0, dash=None):
        pattern = f' stroke-dasharray="{dash}"' if dash else ''
        self.parts.append(f'<line x1="{n(x1)}" y1="{n(y1)}" x2="{n(x2)}" y2="{n(y2)}" stroke="{color}" '
                          f'stroke-width="{n(width)}"{pattern}/>')

    def data(self):
        head = (f'<svg xmlns="http://www.w3.org/2000/svg" width="{self.width}" height="{self.height}" '
                f'viewBox="0 0 {self.width} {self.height}" font-family="{FONT}" role="img">')
        body = [head, f'<title>{escape(self.title)}</title>', f'<desc>{escape(self.description)}</desc>',
                f'<rect x="0" y="0" width="{self.width}" height="{self.height}" fill="{SURFACE}"/>', *self.parts, '</svg>']
        return ('\n'.join(body) + '\n').encode('utf-8')


def legend(svg, x, y, items):
    for name, color in items:
        svg.rect(x, y - 9, 10, 10, color, 2)
        svg.text(x + 14, y, name, 10, color=TEXT2)
        x += 22 + 6.2 * len(name)


def scale(value, low, high, top, bottom):
    return bottom - (value - low) / (high - low) * (bottom - top)


def bars(svg, box, groups, series, low, high, ticks, fmt, title=None):
    """Grouped bars with frozen CI whiskers; non-observed cells are labeled, never drawn as zero."""
    x0, y0, width, height = box
    top, bottom = y0 + (22 if title else 6), y0 + height - 34
    if title:
        svg.text(x0, y0 + 12, title, 11, weight='bold')
    for tick in ticks:
        y = scale(tick, low, high, top, bottom)
        svg.line(x0 + 34, y, x0 + width, y, GRID if tick else AXIS, 1.0 if tick else 1.2)
        svg.text(x0 + 30, y + 3.5, fmt(tick), 9, 'end', TEXT2)
    zero = scale(0.0 if low <= 0 <= high else low, low, high, top, bottom)
    slot = (width - 40) / len(groups)
    bar = min(28.0, slot * 0.78 / len(series))
    for g, group in enumerate(groups):
        centre = x0 + 38 + slot * (g + 0.5)
        svg.text(centre, bottom + 14, group, 9, 'middle', TEXT2)
        start = centre - bar * len(series) / 2
        for s, row in enumerate(series):
            point = row['points'][g]
            x = start + s * bar + 1
            value = point.get('value')
            if value is None:
                svg.text(x + (bar - 2) / 2, zero - 4, point.get('short', 'N/A'), 7, 'middle', MUTED)
                continue
            y = scale(value, low, high, top, bottom)
            color = row['color'](value) if callable(row['color']) else row['color']
            svg.rect(x, min(y, zero), bar - 2, abs(zero - y), color, 2, point.get('tip'))
            upper = y
            if point.get('lo') is not None and point.get('hi') is not None:
                lo, hi = (scale(point[k], low, high, top, bottom) for k in ('lo', 'hi'))
                mid = x + (bar - 2) / 2
                svg.line(mid, lo, mid, hi, TEXT2, 1.0)
                svg.line(mid - 3, lo, mid + 3, lo, TEXT2, 1.0)
                svg.line(mid - 3, hi, mid + 3, hi, TEXT2, 1.0)
                upper = min(upper, hi)
            if point.get('label'):
                below = value < 0
                svg.text(x + (bar - 2) / 2, (max(y, lo if point.get('lo') is not None else y) + 10) if below else upper - 3,
                         point['label'], 7.5, 'middle', TEXT)


def nice_max(values, floor=0.02):
    peak = max([abs(v) for v in values if v is not None] + [floor])
    for limit in (0.02, 0.05, 0.1, 0.15, 0.2, 0.25, 0.4, 0.5, 0.6, 0.8, 1.0):
        if peak * 1.12 <= limit:
            return limit
    return 1.0


def ticks_for(high, low=0.0):
    span = high - low
    step = next(s for s in (0.005, 0.01, 0.02, 0.05, 0.1, 0.2, 0.25, 0.5, 1.0)
                if span / s <= 6 and abs(span / s - round(span / s)) < 1e-9)
    return [round(low + i * step, 10) for i in range(int(round(span / step)) + 1)]


def pct(value):
    return f'{100 * value:.0f}%'


def pct1(value):
    return f'{100 * value:.1f}%'


def axis_format(high):
    return pct if high > 0.1 else pct1


def render(figures):
    """figures: ordered mapping name -> frozen figure spec from cross_regime_synthesis."""
    output = {}
    for name, spec in figures.items():
        output[name + '.svg'] = DRAW[spec['kind']](spec)
    return output


def draw_grouped(spec):
    svg = Svg(760, 446, spec['title'], spec['description'])
    svg.text(16, 24, spec['title'], 14, weight='bold')
    svg.text(16, 42, spec['subtitle'], 10, color=TEXT2)
    if len(spec['series']) > 1:
        legend(svg, 16, 64, [(item['name'], SERIES.get(item['key'], SINGLE)) for item in spec['series']])
    high = spec.get('high') or nice_max([p.get('hi') or p.get('value') for row in spec['series'] for p in row['points']])
    series = [dict(color=SERIES.get(row['key'], SINGLE), points=row['points']) for row in spec['series']]
    bars(svg, (16, 76, 728, 314), spec['groups'], series, 0.0, high, ticks_for(high), axis_format(high))
    svg.text(16, 418, spec['note'], 8.5, color=TEXT2)
    return svg.data()


def draw_panels(spec):
    count = len(spec['panels'])
    width = 250 * count + 20
    svg = Svg(width, 430, spec['title'], spec['description'])
    svg.text(16, 24, spec['title'], 14, weight='bold')
    svg.text(16, 42, spec['subtitle'], 10, color=TEXT2)
    values = [v for p in spec['panels'] for row in p.get('series', ()) for point in row['points']
              for v in (point.get('value'), point.get('lo'), point.get('hi')) if v is not None]
    if spec.get('diverging'):
        bound = max([abs(v) for v in values] + [0.01])
        bound = nice_max([bound], 0.01)
        low, high = -bound, bound
        ticks = ticks_for(high, low)
        fmt = lambda v: f'{v:+.2f}' if v else '0'
    else:
        low, high = 0.0, spec.get('high') or nice_max(values)
        ticks, fmt = ticks_for(high), axis_format(high)
    if spec.get('legend'):
        legend(svg, 16, 64, [(name, SERIES[key]) for name, key in spec['legend']])
    for index, panel in enumerate(spec['panels']):
        box = (10 + 250 * index, 72, 244, 320)
        if panel.get('status'):
            svg.text(box[0] + 12, box[1] + 12, panel['title'], 11, weight='bold')
            svg.rect(box[0] + 34, box[1] + 30, box[2] - 40, box[3] - 70, '#f0efec', 4)
            svg.text(box[0] + 34 + (box[2] - 40) / 2, box[1] + 30 + (box[3] - 70) / 2, panel['status'], 10, 'middle', TEXT2)
            continue
        series = []
        for row in panel['series']:
            color = (lambda v: POSITIVE if v > 0 else NEGATIVE) if spec.get('diverging') else SERIES.get(row.get('key'), SINGLE)
            series.append(dict(color=color, points=row['points']))
        bars(svg, box, panel['groups'], series, low, high, ticks, fmt, panel['title'])
    svg.text(16, 418, spec['note'], 8.5, color=TEXT2)
    return svg.data()


def draw_heatmap(spec):
    rows, columns = spec['rows'], spec['columns']
    cell_w, cell_h, left, top = 78, 40, 96, 104
    svg = Svg(left + cell_w * len(columns) + 24, top + cell_h * len(rows) + 60, spec['title'], spec['description'])
    svg.text(16, 24, spec['title'], 14, weight='bold')
    svg.text(16, 42, spec['subtitle'], 10, color=TEXT2)
    for j, column in enumerate(columns):
        svg.text(left + cell_w * (j + 0.5), top - 22, column['id'], 10, 'middle', weight='bold')
        svg.text(left + cell_w * (j + 0.5), top - 8, column['meaning'], 7.5, 'middle', TEXT2)
    for i, row in enumerate(rows):
        svg.text(left - 8, top + cell_h * (i + 0.5) + 4, row['regime'], 10, 'end')
        for j, cell in enumerate(row['cells']):
            share = cell['fraction']
            shade = SEQUENTIAL[min(len(SEQUENTIAL) - 1, int(share * (len(SEQUENTIAL) - 1) + 0.999999))] if share else SEQUENTIAL[0]
            x, y = left + cell_w * j, top + cell_h * i
            svg.rect(x + 1, y + 1, cell_w - 2, cell_h - 2, shade, 2, f"{row['regime']} {columns[j]['id']}: {cell['count']}/{row['n']}")
            ink = '#ffffff' if share >= 0.5 else TEXT
            svg.text(x + cell_w / 2, y + 17, str(cell['count']), 10, 'middle', ink, 'bold')
            svg.text(x + cell_w / 2, y + 30, pct1(share), 8, 'middle', ink)
    svg.text(16, top + cell_h * len(rows) + 24, spec['note'], 8.5, color=TEXT2)
    return svg.data()


def draw_status(spec):
    svg = Svg(760, 220, spec['title'], spec['description'])
    svg.text(16, 24, spec['title'], 14, weight='bold')
    svg.text(16, 42, spec['subtitle'], 10, color=TEXT2)
    for index, row in enumerate(spec['rows']):
        y = 70 + 40 * index
        svg.rect(16, y, 728, 32, '#f0efec', 4)
        svg.text(28, y + 20, row['label'], 10, weight='bold')
        svg.text(732, y + 20, row['status'], 10, 'end', TEXT2)
    svg.text(16, 208, spec['note'], 8.5, color=TEXT2)
    return svg.data()


DRAW = dict(grouped=draw_grouped, panels=draw_panels, heatmap=draw_heatmap, status=draw_status)
