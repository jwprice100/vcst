library ieee;
use ieee.std_logic_1164.all;
use ieee.numeric_std.all;

entity counter is
generic (
    COUNTER_WIDTH   : positive range 2 to 31;
    COUNTER_WRAP    : positive
);
port (
    clock           : in std_logic;
    enable          : in std_logic;
    reset           : in std_logic;
    counter_value   : out unsigned(COUNTER_WIDTH-1 downto 0)
);
end entity counter;

architecture rtl of counter is
begin
    
    counter_proc: process(clock)
    begin
        if rising_edge(clock) then
            if enable then
                counter_value <= counter_value+1;
                if counter_value = COUNTER_WRAP then
                    counter_value <= (others => '0');
                end if;
            end if;

            if reset then
                counter_value <= (others => '0');
            end if;
        end if;
    end process counter_proc;

end architecture rtl;