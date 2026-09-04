package cn.pokeserver;

import org.bukkit.ChatColor;
import org.bukkit.command.Command;
import org.bukkit.command.CommandExecutor;
import org.bukkit.command.CommandSender;
import org.bukkit.command.TabCompleter;
import org.bukkit.entity.Player;

import java.util.ArrayList;
import java.util.Arrays;
import java.util.List;
import java.util.stream.Collectors;




public class PokeCommands implements CommandExecutor, TabCompleter {

    private final PokePlugin plugin;

    public PokeCommands(PokePlugin plugin) {
        this.plugin = plugin;
    }

    @Override
    public boolean onCommand(CommandSender sender, Command cmd, String label, String[] args) {
        if (!(sender instanceof Player)) {
            sender.sendMessage("该指令仅限游戏内玩家使用。");
            return true;
        }
        Player p = (Player) sender;
        String name = cmd.getName().toLowerCase();

        switch (name) {
            case "poke":
                return help(p);
            case "pokespawn":
                return pokespawn(p);
            case "pokeball":
                return pokeball(p, args);
            case "party":
                return party(p);
            case "box":
                return box(p);
            case "deposit":
                return deposit(p, args);
            case "withdraw":
                return withdraw(p, args);
            case "summon":
                return summon(p, args);
            case "dismiss":
                return dismiss(p);
            case "pokeinfo":
                return info(p, args);
            case "release":
                return release(p, args);
            case "battle":
                return battle(p, args);
            case "attack":
                return attack(p);
            case "heal":
                return heal(p);
        }
        return false;
    }

    private boolean help(Player p) {
        p.sendMessage(ChatColor.GOLD + "══════ 宝可梦帮助 ══════");
        p.sendMessage(ChatColor.YELLOW + "/party" + ChatColor.WHITE + " 查看队伍");
        p.sendMessage(ChatColor.YELLOW + "/box" + ChatColor.WHITE + " 查看存储箱");
        p.sendMessage(ChatColor.YELLOW + "/deposit <序号>" + ChatColor.WHITE + " 存入箱子");
        p.sendMessage(ChatColor.YELLOW + "/withdraw <序号>" + ChatColor.WHITE + " 取出宝可梦");
        p.sendMessage(ChatColor.YELLOW + "/summon <序号>" + ChatColor.WHITE + " 召唤宝可梦");
        p.sendMessage(ChatColor.YELLOW + "/dismiss" + ChatColor.WHITE + " 收回宝可梦");
        p.sendMessage(ChatColor.YELLOW + "/pokeinfo <序号>" + ChatColor.WHITE + " 查看详情");
        p.sendMessage(ChatColor.YELLOW + "/release <序号>" + ChatColor.WHITE + " 放生");
        p.sendMessage(ChatColor.YELLOW + "/battle <玩家>" + ChatColor.WHITE + " 发起对战");
        p.sendMessage(ChatColor.GRAY + "野生宝可梦会随机在附近刷新，手持" + ChatColor.RED + "精灵球"
                + ChatColor.GRAY + "右键捕捉！");
        return true;
    }

    
    private boolean pokespawn(Player p) {
        if (!p.hasPermission("pokeserver.admin")) {
            p.sendMessage(ChatColor.RED + "你没有权限！");
            return true;
        }
        plugin.getManager().spawnWildPokemonNear(p);
        p.sendMessage(ChatColor.GREEN + "已在你的面前刷新了一只野生宝可梦！");
        return true;
    }

    private boolean pokeball(Player p, String[] args) {
        if (!p.hasPermission("pokeserver.admin")) {
            p.sendMessage(ChatColor.RED + "你没有权限！");
            return true;
        }
        int n = 1;
        if (args.length > 0) {
            try { n = Integer.parseInt(args[0]); } catch (NumberFormatException ignore) {}
        }
        plugin.getManager().givePokeball(p, Math.max(1, Math.min(n, 64)));
        p.sendMessage(ChatColor.GREEN + "你获得了 " + n + " 个精灵球！");
        return true;
    }

    private String fmt(Pokemon x) {
        return ChatColor.AQUA + x.getNickname()
                + ChatColor.WHITE + " Lv." + x.getLevel()
                + ChatColor.GRAY + "  EXP " + x.getExp() + "/" + x.expToNext();
    }

    private boolean party(Player p) {
        PlayerData pd = plugin.getManager().getData(p);
        p.sendMessage(ChatColor.GOLD + "════ 我的队伍 (" + pd.getTeam().size() + "/" + PlayerData.MAX_TEAM + ") ════");
        if (pd.getTeam().isEmpty()) {
            p.sendMessage(ChatColor.GRAY + "（还没有宝可梦，去野外捕捉吧！）");
            return true;
        }
        for (int i = 0; i < pd.getTeam().size(); i++) {
            p.sendMessage(ChatColor.YELLOW + "[" + (i + 1) + "] " + fmt(pd.getTeam().get(i)));
        }
        return true;
    }

    private boolean box(Player p) {
        PlayerData pd = plugin.getManager().getData(p);
        p.sendMessage(ChatColor.GOLD + "════ 存储箱 (" + pd.getBox().size() + "/" + PlayerData.MAX_BOX + ") ════");
        if (pd.getBox().isEmpty()) {
            p.sendMessage(ChatColor.GRAY + "（箱子是空的）");
            return true;
        }
        for (int i = 0; i < pd.getBox().size(); i++) {
            p.sendMessage(ChatColor.YELLOW + "[" + (i + 1) + "] " + fmt(pd.getBox().get(i)));
        }
        return true;
    }

    private boolean deposit(Player p, String[] args) {
        int idx = parseIndex(args);
        if (idx < 0) { p.sendMessage(ChatColor.RED + "用法：/deposit <序号>"); return true; }
        PlayerData pd = plugin.getManager().getData(p);
        if (idx >= pd.getTeam().size()) { p.sendMessage(ChatColor.RED + "队伍里没有该序号！"); return true; }
        if (pd.getBox().size() >= PlayerData.MAX_BOX) { p.sendMessage(ChatColor.RED + "箱子已满！"); return true; }
        Pokemon x = pd.getTeam().remove(idx);
        pd.getBox().add(x);
        p.sendMessage(ChatColor.GREEN + "已将 " + ChatColor.AQUA + x.getNickname() + ChatColor.GREEN + " 存入箱子。");
        pd.save(new java.io.File(plugin.getDataFolder(), "players"));
        return true;
    }

    private boolean withdraw(Player p, String[] args) {
        int idx = parseIndex(args);
        if (idx < 0) { p.sendMessage(ChatColor.RED + "用法：/withdraw <序号>"); return true; }
        PlayerData pd = plugin.getManager().getData(p);
        if (idx >= pd.getBox().size()) { p.sendMessage(ChatColor.RED + "箱子里没有该序号！"); return true; }
        if (pd.getTeam().size() >= PlayerData.MAX_TEAM) { p.sendMessage(ChatColor.RED + "队伍已满！"); return true; }
        Pokemon x = pd.getBox().remove(idx);
        pd.getTeam().add(x);
        p.sendMessage(ChatColor.GREEN + "已将 " + ChatColor.AQUA + x.getNickname() + ChatColor.GREEN + " 加入队伍。");
        pd.save(new java.io.File(plugin.getDataFolder(), "players"));
        return true;
    }

    private boolean summon(Player p, String[] args) {
        int idx = parseIndex(args);
        if (idx < 0) { p.sendMessage(ChatColor.RED + "用法：/summon <序号>"); return true; }
        PlayerData pd = plugin.getManager().getData(p);
        if (idx >= pd.getTeam().size()) { p.sendMessage(ChatColor.RED + "队伍里没有该序号！"); return true; }
        plugin.getManager().summon(p, pd.getTeam().get(idx));
        return true;
    }

    private boolean dismiss(Player p) {
        if (!plugin.getManager().hasSummoned(p)) {
            p.sendMessage(ChatColor.RED + "你当前没有召唤宝可梦。");
            return true;
        }
        plugin.getManager().dismiss(p);
        p.sendMessage(ChatColor.GRAY + "已收回宝可梦。");
        return true;
    }

    private boolean info(Player p, String[] args) {
        int idx = parseIndex(args);
        if (idx < 0) { p.sendMessage(ChatColor.RED + "用法：/pokeinfo <序号>"); return true; }
        PlayerData pd = plugin.getManager().getData(p);
        if (idx >= pd.getTeam().size()) { p.sendMessage(ChatColor.RED + "队伍里没有该序号！"); return true; }
        Pokemon x = pd.getTeam().get(idx);
        PokeSpecies.Species sp = PokeSpecies.get(x.getSpecies());
        p.sendMessage(ChatColor.GOLD + "══ " + ChatColor.AQUA + x.getNickname() + ChatColor.GOLD + " ══");
        p.sendMessage(ChatColor.WHITE + "等级: " + ChatColor.YELLOW + x.getLevel());
        p.sendMessage(ChatColor.WHITE + "经验: " + ChatColor.YELLOW + x.getExp() + " / " + x.expToNext());
        p.sendMessage(ChatColor.WHITE + "体力: " + ChatColor.YELLOW + x.getHp() + " / " + x.maxHp());
        if (sp != null && sp.evolveTo != null) {
            p.sendMessage(ChatColor.WHITE + "进化: " + ChatColor.GREEN + "Lv." + sp.evolveLevel
                    + " 时可进化为 " + ChatColor.AQUA + PokeSpecies.get(sp.evolveTo).name);
        } else {
            p.sendMessage(ChatColor.WHITE + "进化: " + ChatColor.GRAY + "已是最强形态");
        }
        return true;
    }

    private boolean release(Player p, String[] args) {
        int idx = parseIndex(args);
        if (idx < 0) { p.sendMessage(ChatColor.RED + "用法：/release <序号>"); return true; }
        PlayerData pd = plugin.getManager().getData(p);
        if (idx >= pd.getTeam().size()) { p.sendMessage(ChatColor.RED + "队伍里没有该序号！"); return true; }
        Pokemon x = pd.getTeam().remove(idx);
        p.sendMessage(ChatColor.GRAY + "你将 " + ChatColor.AQUA + x.getNickname() + ChatColor.GRAY + " 放生了。");
        pd.save(new java.io.File(plugin.getDataFolder(), "players"));
        return true;
    }

    private boolean battle(Player p, String[] args) {
        if (args.length < 1) { p.sendMessage(ChatColor.RED + "用法：/battle <玩家名>"); return true; }
        Player target = plugin.getServer().getPlayer(args[0]);
        if (target == null) { p.sendMessage(ChatColor.RED + "找不到该玩家！"); return true; }
        if (target.equals(p)) { p.sendMessage(ChatColor.RED + "不能和自己对战！"); return true; }
        plugin.getBattleManager().startBattle(p, target);
        return true;
    }

    private boolean attack(Player p) {
        plugin.getBattleManager().attack(p);
        return true;
    }

    private boolean heal(Player p) {
        plugin.getBattleManager().heal(p);
        return true;
    }

    private int parseIndex(String[] args) {
        if (args.length < 1) return -1;
        try {
            int i = Integer.parseInt(args[0]) - 1;
            return i < 0 ? -1 : i;
        } catch (NumberFormatException e) {
            return -1;
        }
    }

    @Override
    public List<String> onTabComplete(CommandSender sender, Command cmd, String alias, String[] args) {
        if (cmd.getName().equalsIgnoreCase("battle") && args.length == 1) {
            String prefix = args[0].toLowerCase();
            return plugin.getServer().getOnlinePlayers().stream()
                    .map(Player::getName)
                    .filter(n -> n.toLowerCase().startsWith(prefix))
                    .collect(Collectors.toList());
        }
        return new ArrayList<>();
    }
}
