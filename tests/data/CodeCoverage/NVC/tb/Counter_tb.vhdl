library ieee;
use     ieee.std_logic_1164.all;
use     ieee.numeric_std.all;

use     work.Utilities.all;


entity Counter_tb is
	generic (
		CYCLES : positive := 20;
		RESETS : boolean  := false
	);
end entity;


architecture sim of Counter_tb is
	signal Clock  : std_logic := '0';
	signal Reset  : std_logic := '0';
	signal Enable : std_logic := '0';
	signal Mode   : std_logic_vector(1 downto 0) := "00";
	signal Value  : unsigned(3 downto 0);
	signal Wrap   : std_logic;
	signal Wide   : unsigned(7 downto 0);
	signal Done   : boolean   := false;
begin
	Clock <= not Clock after 5 ns when not Done;

	DUT: entity work.Counter
		generic map (
			BITS => 4
		)
		port map (
			Clock  => Clock,
			Reset  => Reset,
			Enable => Enable,
			Mode   => Mode,
			Value  => Value,
			Wrap   => Wrap
		);

	WideDUT: entity work.Counter
		generic map (
			BITS => 8
		)
		port map (
			Clock  => Clock,
			Reset  => Reset,
			Enable => Enable,
			Mode   => Mode,
			Value  => Wide,
			Wrap   => open
		);

	Stimuli: process
	begin
		Enable <= '1';
		for i in 1 to CYCLES loop
			wait until rising_edge(Clock);
			if i = CYCLES / 2 then
				Mode <= "01";
			end if;

			if RESETS and i mod 4 = 0 then
				Reset <= '1';
			else
				Reset <= '0';
			end if;
		end loop;
		wait until rising_edge(Clock);

		report "Value: " & integer'image(Maximum(to_integer(Value), to_integer(Wide)));
		Done <= true;
		wait;
	end process;
end architecture;
