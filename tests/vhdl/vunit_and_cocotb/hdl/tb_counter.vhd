library ieee;
use ieee.std_logic_1164.all;
use ieee.numeric_std.all;

library vunit_lib;
context vunit_lib.vunit_context;

entity tb_counter is
generic (
    COUNTER_WIDTH   : positive range 2 to 31;
    COUNTER_WRAP    : positive;
    runner_cfg      : string
);
end entity tb_counter;

architecture rtl of tb_counter is
    signal clock           : std_logic := '0';
    signal enable          : std_logic := '0';
    signal reset           : std_logic := '0';
    signal counter_value   : unsigned(COUNTER_WIDTH-1 downto 0);

begin

    dut: entity work.counter
    generic map (
        COUNTER_WIDTH   => COUNTER_WIDTH,
        COUNTER_WRAP    => COUNTER_WRAP
    )
    port map (
        clock           => clock,
        enable          => enable,
        reset           => reset,
        counter_value   => counter_value
    );

    clock <= not clock after 4 ns;

    test_runner: process
    begin
        test_runner_setup(runner, runner_cfg);

        while test_suite loop
            if run("reset_test") then
                wait until rising_edge(clock);   
                reset <= '1';
                wait until rising_edge(clock);            
                wait until rising_edge(clock);         
                check_equal(counter_value, 0, "Counter did not initialize to zero.");
            elsif run("count_test") then
                reset <= '1';
                wait until rising_edge(clock);   
                reset  <= '0';
                enable <= '1';
                wait until rising_edge(clock);   
                
                for i in 0 to COUNTER_WRAP loop
                    check_equal(counter_value, i, "Counter value was not correct.");
                    wait until rising_edge(clock);   
                end loop;
            elsif run("wrap_test") then
                reset <= '1';
                wait until rising_edge(clock);   
                reset  <= '0';
                enable <= '1';
                wait until rising_edge(clock);               
                for i in 0 to COUNTER_WRAP-1 loop
                    wait until rising_edge(clock);   
                end loop;

                check_equal(counter_value, COUNTER_WRAP, "Counter value did not reach last value before wrap.");
                wait until rising_edge(clock);   
                check_equal(counter_value, 0, "Counter value did not wrap.");
            end if;
        end loop;

        test_runner_cleanup(runner);
    end process test_runner;




end architecture rtl;