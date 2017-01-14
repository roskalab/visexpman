class LickDetector {
    public:
        LickDetector(void);
        void update(void);
        void reset(void);
        int get_lick_number(void);
        float get_last_lick_time(void);
        unsigned long first_lick_time;
    private:
        bool rise;
        unsigned long last_run;
        unsigned long rise_time;
        unsigned long last_lick_time;
        int lick_counter;
        int voltage_threshold_adc;
        unsigned long duration_max_ms;
        unsigned long duration_min_ms;
        unsigned long timestamp;
        unsigned long dt;
        int adc_val;
};
