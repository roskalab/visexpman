
class Dac {
    public:
        Dac(void);
        void set(float voltage);
        void spi_transfer(char c);
        int check_output(float expected_voltage);
        int test(void);
};
