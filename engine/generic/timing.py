import numpy # For some unknown reason numpy is not imported without errors
import unittest

def schedule_fragments(period_time, repeats, maximum_duration):
    '''
    Calculates fragment durations
    '''
    required_time = period_time * repeats
    if required_time <= maximum_duration:
        fragment_durations = [required_time]
    else:
        repetition_per_fragment = numpy.floor(maximum_duration / float(period_time))
        number_of_fragments = int(repeats) / int(repetition_per_fragment)        
        number_of_repeats_in_last_fragment = int(repeats) % int(repetition_per_fragment)        
        fragment_durations = [repetition_per_fragment * period_time] * number_of_fragments
        if number_of_repeats_in_last_fragment > 0:
            fragment_durations.append(float(number_of_repeats_in_last_fragment * period_time))
    repeats_per_fragment = []
    for fragment_duration in fragment_durations:
        repeats_per_fragment.append(fragment_duration / period_time)
    return fragment_durations, repeats_per_fragment


class TestTiming(unittest.TestCase):
    def test_01_fits_one_fragment(self):
        period_time = 5
        repeats = 5
        maximum_duration = 100
        self.assertEqual(schedule_fragments(period_time, repeats, maximum_duration)[0], [period_time*repeats])
        
    def test_02_fits_one_fragment(self):
        period_time = 5
        repeats = 5
        maximum_duration = 25.0
        self.assertEqual(schedule_fragments(period_time, repeats, maximum_duration)[0], [period_time*repeats])
        
    def test_03_fits_to_multiple_fragment(self):
        period_time = 5
        repeats = 10
        maximum_duration = 21
        schedule = [period_time*4, period_time*4, period_time*2]
        self.assertEqual(schedule_fragments(period_time, repeats, maximum_duration)[0], schedule)
        
        
    def test_04_fits_to_multiple_fragment(self):
        period_time = 5.0
        repeats = 10
        maximum_duration = 15
        schedule = [period_time*3, period_time*3, period_time*3, period_time]
        self.assertEqual(schedule_fragments(period_time, repeats, maximum_duration)[0], schedule)
    
if __name__ == "__main__":
    unittest.main()
