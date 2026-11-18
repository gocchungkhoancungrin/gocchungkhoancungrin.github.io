"""Lấy dữ liệu cổ phiếu: chỉ số từ TradingView scanner, lịch sử giá từ VNDirect.
Ghi ra thư mục hiện tại: quotes.json và hist/<MÃ>.json"""
import json, os, sys, time, urllib.request, datetime
from concurrent.futures import ThreadPoolExecutor

NAMES = {
 'FPT':'Tập đoàn FPT','VCB':'Ngân hàng Vietcombank','HPG':'Tập đoàn Hòa Phát','MWG':'Thế Giới Di Động',
 'SSI':'Chứng khoán SSI','FTS':'Chứng khoán FPT','SHS':'Chứng khoán Sài Gòn – Hà Nội','HDB':'Ngân hàng HDBank',
 'CTG':'Ngân hàng VietinBank','BID':'Ngân hàng BIDV','TCB':'Ngân hàng Techcombank','MBB':'Ngân hàng MB',
 'VPB':'Ngân hàng VPBank','ACB':'Ngân hàng ACB','STB':'Ngân hàng Sacombank','VIB':'Ngân hàng VIB',
 'LPB':'Ngân hàng LPBank','SSB':'Ngân hàng SeABank','VHM':'Vinhomes','VIC':'Vingroup','VRE':'Vincom Retail',
 'VNM':'Vinamilk','MSN':'Tập đoàn Masan','SAB':'Sabeco','GAS':'PV Gas','PLX':'Petrolimex','POW':'PV Power',
 'BSR':'Lọc hóa dầu Bình Sơn','GVR':'Cao su Việt Nam','FRT':'FPT Retail','PNJ':'Vàng bạc đá quý Phú Nhuận',
 'VND':'Chứng khoán VNDirect','VCI':'Chứng khoán Vietcap','HCM':'Chứng khoán HSC','DGC':'Hóa chất Đức Giang',
 'REE':'Cơ điện lạnh REE','KDH':'Khang Điền','NLG':'Nam Long','DXG':'Đất Xanh','PVD':'PV Drilling','HSG':'Hoa Sen',
}
COLS = ['name','description','open','high','low','close','change','volume','market_cap_basic','price_earnings_ttm','price_book_fq',
 'earnings_per_share_basic_ttm','book_value_per_share_fq','price_52_week_high','price_52_week_low',
 'return_on_equity_fq','return_on_assets_fq','net_margin_ttm','gross_margin_ttm','operating_margin_ttm',
 'debt_to_equity_fq','current_ratio_fq','dividend_yield_recent','total_revenue_yoy_growth_ttm',
 'earnings_per_share_diluted_yoy_growth_ttm','enterprise_value_ebitda_ttm','sector','industry','exchange']

def http(url, data=None, tries=3):
    for i in range(tries):
        try:
            req = urllib.request.Request(url, data=data, headers={'User-Agent':'Mozilla/5.0','Content-Type':'application/json'})
            return json.load(urllib.request.urlopen(req, timeout=30))
        except Exception as e:
            print('lỗi', url[:80], e, file=sys.stderr)
            time.sleep(2 * (i + 1))
    return None

def r(x, n=2):
    return None if x is None else round(x, n)

body = json.dumps({'markets':['vietnam'],'symbols':{'query':{'types':['stock']}},
    'columns':COLS,'range':[0,2000]}).encode()
sc = http('https://scanner.tradingview.com/vietnam/scan', body)
if not sc or not sc.get('data'):
    sys.exit('Không lấy được dữ liệu TradingView')
quotes = {}
for row in sc['data']:
    d = dict(zip(COLS, row['d']))
    t = d['name']
    if not t or len(t) > 5 or d['close'] is None or d['exchange'] not in ('HOSE','HNX','UPCOM'):
        continue
    quotes[t] = {'n':NAMES.get(t) or d['description'],'ex':d['exchange'],'p':d['close'],'ch':r(d['change']),'v':d['volume'],
        'o':d['open'],'h':d['high'],'l':d['low'],
        'mc':d['market_cap_basic'],'pe':r(d['price_earnings_ttm']),'pb':r(d['price_book_fq']),
        'eps':r(d['earnings_per_share_basic_ttm'],0),'bv':r(d['book_value_per_share_fq'],0),
        'hi':r(d['price_52_week_high'],0),'lo':r(d['price_52_week_low'],0),'roe':r(d['return_on_equity_fq']),
        'roa':r(d['return_on_assets_fq']),'nm':r(d['net_margin_ttm']),'gm':r(d['gross_margin_ttm']),
        'om':r(d['operating_margin_ttm']),'de':r(d['debt_to_equity_fq']),'cr':r(d['current_ratio_fq']),
        'dy':r(d['dividend_yield_recent']),'rg':r(d['total_revenue_yoy_growth_ttm']),
        'eg':r(d['earnings_per_share_diluted_yoy_growth_ttm']),'ev':r(d['enterprise_value_ebitda_ttm']),
        'sec':d['sector'],'ind':d['industry']}
    quotes[t] = {k: v for k, v in quotes[t].items() if v is not None}
vn = datetime.datetime.utcnow() + datetime.timedelta(hours=7)
os.makedirs('hist', exist_ok=True)
frm = (vn - datetime.timedelta(days=400)).strftime('%Y-%m-%d')
ok = 0
if os.environ.get('HIST') == '1':
    def one(t):
        h = http('https://api-finfo.vndirect.com.vn/v4/stock_prices?q=code:%s~date:gte:%s&sort=date&size=400' % (t, frm), tries=2)
        if not h or not h.get('data'):
            return 0
        rows = []
        for x in reversed(h['data']):
            try:
                rows.append([x['date'], round(x['adOpen']*1000), round(x['adHigh']*1000), round(x['adLow']*1000),
                             round(x['adClose']*1000), int((x.get('nmVolume') or 0) + (x.get('ptVolume') or 0))])
            except Exception:
                pass
        if rows:
            json.dump(rows, open('hist/%s.json' % t, 'w'), separators=(',',':'))
            return 1
        return 0
    with ThreadPoolExecutor(max_workers=6) as ex:
        ok = sum(ex.map(one, list(quotes)))
json.dump({'updated': vn.strftime('%Y-%m-%d %H:%M:%S'), 'quotes': quotes}, open('quotes.json','w'),
          ensure_ascii=False, separators=(',',':'))
print('quotes', len(quotes), 'hist', ok)
