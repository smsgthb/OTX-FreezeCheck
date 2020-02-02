#! python3
# Analyse  FrSky LockOut
# HF-Strecke unterbrochen, z.T. extreme Servo-Ausschläge (falls fehlerhafte Werte bei Beginn des Lockouts)
# Dauer meist 0,9 s dann Sync mit Tx OK
# -- Telemetrie-Log: Einfrieren der Werte vom Rx, Tx-Werte laufen weiter
# -- fehlerhafte Servo-Ausschläge nicht sichtbar, da Geberwerte vom Tx im Log

import csv, os, re, sys

if len(sys.argv) <2:
	print("usage: %s [Dateiname]" % (sys.argv[0]))
	sys.exit()

# Logdatei - Input
csvFilename = sys.argv[1]

# Skript-Ausgabe auch in Log-Datei
log_outName = sys.argv[1].replace(".csv",".log")
log_out = open(log_outName,"w")

# Ausgabe in Log und auf Konsole
def print_Console_Log(OStr):
	print(OStr)
	log_out.write(OStr + "\n")

# Optional - Mindest-Zeitinvervall
try: 
	dt_min = int(sys.argv[2])
except IndexError:
	outStr="Error: Mindestschwelle dt ungültig oder nicht gesetzt => Default >800"
	print_Console_Log(outStr)
	dt_min = 800

logFile = open(csvFilename)
readerObj = csv.reader(logFile)
csvRows = []
old_t_ms = 0
RSSI = 0
n=0
flag = 0
R_Date = 0
Tx=[9999]
ErrorStart=[]
ErrorEnd=[]

def get_index(col_name):
	try:
		return row.index(col_name)
	except ValueError:
		dummy = 0

# Zeitstring: Umrechnung in Millisekunden
def ms_timestamp(tStr):
	t=re.compile("[.:]").split(tStr)
	ms = int(t[0])*60*60*1000 + int(t[1])*60*1000 + int(t[2])*1000 + int(t[3])
	return ms

for row in readerObj:
	if readerObj.line_num == 1:

		# Ermittle Spalten-Nummer für RSSI(dB)
		R_RSSI = get_index('RSSI(dB)')
		R_RxBt = get_index('RxBt(V)')
		# Sei,Hƒh,Gas,Que oder Sei,H�h,Gas,Que  engl.: Rud,Ele,Thr,Ail
		Tx.extend((get_index("Sei"), get_index("Rud"), get_index("Ele"), get_index("Hƒh"), get_index("H�h"), get_index("Höh"),get_index("Thr"), get_index("Gas"), get_index("Ail"), get_index("Que")))
		# "None" Einträge entfernen und Minimum suchen
		R_Tx = min(list(filter(None,Tx)))
		print_Console_Log("1. TX-Spalte: " + str(R_Tx))

		# CSV-Kopfzeile
		HeaderStr=",".join(row) + "\n"
		print_Console_Log('Vergleichswerte: ' + ",".join(row[2:R_Tx]))
	
	# ab hier Telemetrie-Zeilen
	else:
		t_ms = ms_timestamp(row[1])
		t_diff = t_ms - old_t_ms
		
		Zeit = row[1]
		RSSI = int(row[R_RSSI])
		RxBt = float(row[R_RxBt])
		
		# Telemetriezeile ohne ZeitStr und Tx-Werte
		TStr = str(row[2:R_Tx])

		# RSSI und RxBt sind Null
		# aktuelle Zeile identisch mit vorheriger
		if readerObj.line_num > 2 and TStr == old_TStr and RSSI > 0 and RxBt > 0.0:
			if flag == 0:
				ErrorStart.append(readerObj.line_num-1)
				flag = 1
				Start_ms = old_t_ms # vorherigen TimeStamp ist Startzeit für "Hänger"
				Start_Zeit = old_Zeit
				h_RSSI = old_RSSI
		else:
			if flag == 1:
				flag = 0
				hang_ms = t_ms - Start_ms
				if hang_ms > dt_min and t_diff < 4000:
					ErrorEnd.append(readerObj.line_num)
					print_Console_Log("n=%04d t=%s-%s dt=%5d  RSSI=%03d" % (readerObj.line_num, Start_Zeit, Zeit, hang_ms, old_RSSI))
				else:
					ErrorStart.pop() # Wenn Zeitspanne kleiner als dt_min: Fehlereintrag wird wieder entfernt.
					
		# Werte speichern
		old_t_ms = t_ms # TimeStamp merken
		old_Zeit = Zeit
		old_RSSI = RSSI 
		old_row = row
		old_TStr = TStr
logFile.close()
# Fehler am Ende? -- Flag noch 1
if flag == 1:
	flag = 0
	hang_ms = t_ms - Start_ms
	if hang_ms > dt_min and t_diff < 4000:
		ErrorEnd.append(readerObj.line_num)
		print_Console_Log("End: n=%04d t=%s-%s dt=%5d  RSSI=%03d" % (readerObj.line_num, Start_Zeit, Zeit, hang_ms, old_RSSI))

# Evtl. noch ErrorStart Eintrag ohne "Ende" im Array - ErrorStart auf Länge von ErrorEnd bringen
del ErrorStart[len(ErrorEnd):]

csv_in = open(csvFilename).readlines() # gesamte Datei eingelesen

# Zeitdifferenz zwischen Logeinträgen ermitteln
logdiff_ms=ms_timestamp(csv_in[3].split(",")[1])-ms_timestamp(csv_in[2].split(",")[1])
print_Console_Log('LogDiff ' + str(logdiff_ms) + "ms")
lines_5s = int(5000 / logdiff_ms)

# CSV-Output Datei - nur Fehlerzeilen
csv_outName = sys.argv[1].replace(".csv","_err.csv")
csv_out = open(csv_outName,"w")
csv_out.write(HeaderStr)
print_Console_Log("Fehler: " + str(len(ErrorStart)))

for i in range(len(ErrorStart)):
	s = ErrorStart[i]-lines_5s
	if s<0:
		s=0
	e = ErrorEnd[i]+lines_5s
	if e >= len(csv_in):
		e = len(csv_in)
	print_Console_Log("Err %d: %d-%d (%d-%d)" % (i, ErrorStart[i],ErrorEnd[i],s,e))
	csv_out.write(''.join((csv_in[s:e])))
csv_out.close()
