#!/usr/bin/python

def PrintOneLine(table_header, col_len, silent_column = []):
  silent_column = set(silent_column)
  line = '|'
  for i in range(len(col_len)):
    if col_len[i] == 0: continue
    if table_header[i] in silent_column: continue
    line += '-' * col_len[i] + '|'
  return line

def PrintTable(table_header, records, silent_column = [], truncate_float = True, header_transformer = lambda name: name,
               float_precision = 3):
  silent_column = set(silent_column)
  col_len = [0] * len(table_header)
  for cells in records:
    for i in range(len(cells)):
      if truncate_float and isinstance(cells[i], float):
        if float_precision > 0:
          cells[i] = str(round(cells[i], float_precision))
        else:
          cells[i] = str(int(cells[i]))
      col_len[i] = max(col_len[i], len(str(cells[i])))
  for i in range(len(col_len)):
    if col_len[i] > 0:
      col_len[i] = max(col_len[i], len(header_transformer(table_header[i])))
  line = PrintOneLine(map(header_transformer, table_header), col_len, silent_column)
  header = '+' + line[1:len(line) - 1] + '+'
  print(header)
  records.insert(0, map(header_transformer, table_header))
  first = True
  for cells in records:
    assert len(cells) == len(records[0])
    row = '|'
    for i in range(len(cells)):
      if col_len[i] == 0: continue
      if table_header[i] in silent_column: continue
      row += (' ' * (col_len[i] - len(str(cells[i])))) + str(cells[i]) + '|'
    if first: first = False
    else: print(line)
    print(row)
  print(header)

# 'records_map' are an array of map.
def PrintTableMap(table_header, records_map, silent_column = [], truncate_float = True, header_transformer = lambda name: name,
                  float_precision = 3):
  records = []
  for r in records_map:
    records.append([r.get(col, '') for col in table_header])
  PrintTable(table_header, records, silent_column, truncate_float, header_transformer, float_precision)
