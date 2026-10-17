use work.Classify.all;


entity Testbench is
end entity;


architecture sim of Testbench is
begin
	process
		variable sum : integer := 0;
	begin
		for i in 1 to 3 loop
			sum := sum + Sign(i);
			if InRange(i, 2, 5) then
				sum := sum + i;
			end if;
		end loop;

		report "sum = " & integer'image(sum);
		wait;
	end process;
end architecture;
