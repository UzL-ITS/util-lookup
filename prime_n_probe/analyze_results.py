import os
import argparse
import statistics
import numpy
import matplotlib.pyplot as plt
import matplotlib as mpl

line1 = ['+', '-', '/', '0', '1', '2', '3', '4', '5', '6', '7', '8', '9', '=']
line2 = ['A', 'B', 'C', 'D', 'E', 'F', 'G', 'H', 'I', 'J', 'K', 'L', 'M', 'N', 'O',
         'P', 'Q', 'R', 'S', 'T', 'U', 'V', 'W', 'X', 'Y', 'Z', 'a', 'b', 'c', 'd',
         'e', 'f', 'g', 'h', 'i', 'j', 'k', 'l', 'm', 'n', 'o', 'p', 'q', 'r', 's',
         't', 'u', 'v', 'w', 'x', 'y', 'z']

ref_value = 'MIICdwIBADANBgkqhkiG9w0BAQEFAASCAmEwggJdAgEAAoGBAMUwt5PUgUIj6/F33WuawCxFBeZEIBxeix2mPfR3x94qzFmvFPVrnXBI8aRAhY+CuWx6jPJ/jnQvQcsyHHyFFE6h9xe31R86WUMh2uq1Ny7wGU2wRIr6YlHjKAh5gDLzCL3XGzv72dv0clbOTUZHVGGFd5OX0KRk/Am0w+j8JKkzAgMBAAECgYB2Jq6YYSfh3WwuDsgZBWxIGkNiqUckOHHanhVZObwEHli7E/DW7Fg1Qz+mTxK33ngDy5pQYqWUcAxYF/qBkauMM9xNgwdc6JCjyztM6g0j81QHduQs+QPnRIYZDoPIc5HX0EVcwTjfH2tmQMvB7THFQuDerIMgLh/pRDd59hd5oQJBAPNdo3SJxnlvfMxjWq6naJnp1n9+E7lvo5qNNjpSnKCszo8vwpvML6hNiG0FFRKnyg8AM8QE09U/rvsw66Iz6B8CQQDPbWaaTutwOF5+x30Bq/os07vb3sVLh5RwNQgXnQxF7nDEP5ECqQnwVeYOjU4egrIVV0NeOnSu7GstxPcpKqxtAkArlofiJZMQyPEXQmxJf95yQrmSWCh8PAyXb9dYltdKx+ivKKS4dtfKUyiuLgzaLIc6LJUY9KxkM2XJw7dQc++NAkEAwG5u1FLIyugQii8JgoaIZhPb4ONvR121UM9x/W4d17aX+Qg7wCsP5F3cOr3OrjFzgqbdAcrbOvhrih+DaDaFlQJBAIkoJMeTMM8p8PJki3Yfsetvg/WewB71UOAdr0sJRi7w6hPjMFOgc+JJg78S/0NbFu49HgkmobNOGJpUhF3CjBk='

def get_by_title(title, file_content):
    content = file_content.split('\n')
    out_str = str()

    for i in range(len(content)):
        if content[i] == title:
            out_str = content[i+1]

    return out_str


def convert_to_int_array(offline_analysis_str):
    out = []
    for c in offline_analysis_str:
        out.append(c)
    return out


def get_content(filename):
    with open(filename, 'r') as f:
        file_content = f.read()
        online_analysis_str = get_by_title('Prime and Probe (online analysis)', file_content)
        offline_analysis_str = get_by_title('Prime and Probe (offline analysis):', file_content)
        extracted_pattern_offline_str = get_by_title('Relevant key accesses from PnP (offline):', file_content)

        online_analysis = convert_to_int_array(online_analysis_str)
        offline_analysis = convert_to_int_array(offline_analysis_str)
        extracted_pattern_offline = convert_to_int_array(extracted_pattern_offline_str)

    return online_analysis, offline_analysis, extracted_pattern_offline


def main(args):
#    mpl.use('agg')
    results = {}
    cur = 0
    for filename in os.listdir(args.folder):
        online_analysis, offline_analysis, extracted_pattern_offline = get_content(os.path.join(args.folder, filename))
        results[cur] = {}
        results[cur]['online_analysis'] = online_analysis
        results[cur]['offline_analysis'] = offline_analysis
        results[cur]['extracted_pattern_offline'] = extracted_pattern_offline

        cur += 1

    result_correct_sequence_length = {}
    result_incorrect_sequence_length = {}

    for key, value in results.items():
        if len(value['extracted_pattern_offline']) == 848:
            result_correct_sequence_length[key] = value
        else:
            result_incorrect_sequence_length[key] = value

    for key, value in result_correct_sequence_length.items():
        unsure_count = 0
        false_classification_count = 0
        i = 0
        for s in value['extracted_pattern_offline']:
            if s == 'x':
                unsure_count += 1
            elif s == '1':
                if not(ref_value[i] in line1):
                    false_classification_count += 1
            elif s == '2':
                if not(ref_value[i] in line2):
                    false_classification_count += 1
            i += 1

        value['unsure_count'] = unsure_count
        value['false_classification_count'] = false_classification_count

    unsure_count_array = []
    false_classification_array = []
    missing_or_wrong_classification_array = []

    for key, value in result_correct_sequence_length.items():
        unsure_count_array.append(value['unsure_count'])
        false_classification_array.append(value['false_classification_count'])
        missing_or_wrong_classification_array.append(value['unsure_count'] + value['false_classification_count'])

    mean_unsure_count = statistics.mean(unsure_count_array)
    median_unsure_count = statistics.median(unsure_count_array)
    stdev_unsure_count = statistics.stdev(unsure_count_array)

    mean_false_classification_count = statistics.mean(false_classification_array)
    median_false_classification_count = statistics.median(false_classification_array)
    stdev_false_classification_count = statistics.stdev(false_classification_array)

    mean_missing_or_wrong_classification_count = statistics.mean(missing_or_wrong_classification_array)
    median_missing_or_wrong_classification_count = statistics.median(missing_or_wrong_classification_array)
    stdev_missing_or_wrong_classification_count = statistics.stdev(missing_or_wrong_classification_array)

    zero_unsure_count = 0
    one_unsure_count = 0
    two_unsure_count = 0
    three_unsure_count = 0
    four_unsure_count = 0
    five_unsure_count = 0
    
    smaller_ten_unsure_count = 0    

    best_unsure_count = 848
    worst_unsure_count = 0

    for u in unsure_count_array:
        if u == 0:
            zero_unsure_count += 1
        if u == 1:
            one_unsure_count += 1
        if u == 2:
            two_unsure_count += 1
        if u == 3:
            three_unsure_count += 1
        if u == 4:
            four_unsure_count += 1
        if u == 5:
            five_unsure_count += 1
        if u < 10:
            smaller_ten_unsure_count += 1
        if u < best_unsure_count:
            best_unsure_count = u
        if u > worst_unsure_count:
            worst_unsure_count = u

    zero_wrong_or_missing_count = 0
    for wm in missing_or_wrong_classification_array:
        if wm == 0:
            zero_wrong_or_missing_count += 1


    print('Number of examples with wrong sequence extraction: ' + str(len(result_incorrect_sequence_length)))
    print('Number of examples with correct sequence extraction: ' + str(len(result_correct_sequence_length)))

    print('Mean unsure count (correct sequence): ' + str(mean_unsure_count))
    print('Median unsure count (correct sequence): ' + str(median_unsure_count))
    print('Stddev unsure count (correct sequence): ' + str(stdev_unsure_count))
    print('Number of examples with unsure count = 0: ' + str(zero_unsure_count))
    print('Number of examples with unsure count = 1: ' + str(one_unsure_count))
    print('Number of examples with unsure count = 2: ' + str(two_unsure_count))
    print('Number of examples with unsure count = 3: ' + str(three_unsure_count))
    print('Number of examples with unsure count = 4: ' + str(four_unsure_count))
    print('Number of examples with unsure count = 5: ' + str(five_unsure_count))
    print('Number of examples with unsure count < 10: ' + str(smaller_ten_unsure_count))
    print('Best unsure count: ' + str(best_unsure_count))
    print('Worst unsure count: ' + str(worst_unsure_count))

    print('Mean number of false classifications (correct sequence): ' + str(mean_false_classification_count))
    print('Median number of false classifications (correct sequence): ' + str(median_false_classification_count))
    print('Stddev number of false classifications (correct sequence): ' + str(stdev_false_classification_count))

    print('Mean number of wrong or missing classifications (correct sequence): ' + str(mean_missing_or_wrong_classification_count))
    print('Median number of wrong or missing classifications (correct sequence): ' + str(median_missing_or_wrong_classification_count))
    print('Stddev number of wrong or missing classifications (correct sequence): ' + str(stdev_missing_or_wrong_classification_count))

    print('Number of examples with wrong or missing classifications count = 0: ' + str(zero_wrong_or_missing_count))

    # plt.title('Unsure count')
   
    plt.rc('xtick', labelsize=20)
    plt.rc('ytick', labelsize=20)
    plt.rc('axes', labelsize=22) 
    plt.figure(figsize=(14,9))
    # plt.xlabel('# ambiguous classifications')
    plt.xlabel('# wrong or ambiguous classifications')
    plt.ylabel('# of executions')
    # plt.hist(unsure_count_array, bins=50, alpha=0.5)
    plt.hist(missing_or_wrong_classification_array, bins=50, alpha=0.5, color='green', label="LOAD")
    plt.legend(loc="upper right", prop={'size': 22})
    x_ticks = numpy.arange(0,200,10)
    plt.xticks(x_ticks, rotation='vertical')
   # plt.savefig('ambiguous_count.eps')
    plt.savefig('ambiguous_count.pdf')
    plt.show()


if __name__ == '__main__':
    default_folder_name = 'paper_meas'
    arg_parser = argparse.ArgumentParser(description='Analyze parsed results of pnp cache attack on b64 dec.')
    arg_parser.add_argument('--folder', nargs='?', const=default_folder_name,
                            default=default_folder_name, type=str)
    args = arg_parser.parse_args()
    main(args)
