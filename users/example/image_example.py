#user_log_file_path = '/home/log.txt'

example = 1

for i in range(2):
    if not self.config.SHOW_ALL_EXAMPLES:
        example_i = example
    else:
        example_i = i
    if example_i == 0:
        parameters = [100.0,  100.0]
        formula_pos_x = ['p[0] * cos(10.0 * t)',  parameters]
        formula_pos_y = ['p[1] * sin(10.0 * t)',  parameters]            
        formula = [formula_pos_x,  formula_pos_y]
        self.st.show_image('../../presentinator/data/stimulation_data/images',  0.0,  (0, 0), formula)
        self.st.show_image(self.config.DEFAULT_IMAGE_PATH,  1.0,  (0, 0), formula = formula)
        
    elif example_i == 1:
        self.st.show_image(self.config.DEFAULT_IMAGE_PATH,  1.0,  (300, 0))
