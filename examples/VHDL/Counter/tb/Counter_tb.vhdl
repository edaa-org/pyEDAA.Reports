library ieee;
use     ieee.std_logic_1164.all;
use     ieee.numeric_std.all;

use     work.Functions.all;


entity Counter_tb is
	generic (
		CYCLES : positive := 20;
		RESETS : boolean  := false
	);
end entity;


architecture sim of Counter_tb is
	constant BITS : positive := log2ceil(CYCLES);

	signal Clock  : std_logic := '0';
	signal Reset  : std_logic := '0';
	signal Enable : std_logic := '0';
	signal Value  : unsigned(BITS - 1 downto 0);
	signal Wrap   : std_logic;
	signal Done   : boolean   := false;
begin
	Clock <= not Clock after 5 ns when not Done;

	DUT: entity work.Counter
		generic map (
			BITS => BITS
		)
		port map (
			Clock  => Clock,
			Reset  => Reset,
			Enable => Enable,
			Value  => Value,
			Wrap   => Wrap
		);

	Stimuli: process
	begin
		for i in 1 to CYCLES loop
			wait until rising_edge(Clock);
			case i mod 4 is
				when 0 =>
					Enable <= '0';
					Reset  <= '0';
				when 1 | 2 =>
					Enable <= '1';
				when others =>
					if RESETS then
						Reset <= '1';
					end if;
			end case;
		end loop;
		wait until rising_edge(Clock);

		report "Value: " & integer'image(max(to_integer(Value), CYCLES));
		Done <= true;
		wait;
	end process;

	Checker: process(Clock)
	begin
		if rising_edge(Clock) and Wrap = '1' then
			report "Counter wrapped." severity note;
		end if;
	end process;
end architecture;
