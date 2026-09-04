package cn.pokeserver;

import org.bukkit.ChatColor;
import org.bukkit.Sound;
import org.bukkit.entity.Player;

import java.util.HashMap;
import java.util.Map;
import java.util.UUID;





public class BattleManager {

    private final PokePlugin plugin;
    private final Map<UUID, Battle> battles = new HashMap<>();

    public BattleManager(PokePlugin plugin) {
        this.plugin = plugin;
    }

    private static class Battle {
        Player p1, p2;
        String n1, n2;
        int hp1, hp2;
        int lv1, lv2;
        UUID turn;
        boolean heal1, heal2;
        int expReward;
    }

    public boolean isInBattle(Player p) {
        return battles.containsKey(p.getUniqueId());
    }

    public void removePlayer(Player p) {
        Battle b = battles.remove(p.getUniqueId());
        if (b == null) return;
        
        Player other = b.p1.equals(p) ? b.p2 : b.p1;
        battles.remove(other.getUniqueId());
        Player winner = other;
        if (winner.isOnline()) {
            winner.sendMessage(ChatColor.GOLD + "★ 对战胜利！" + ChatColor.GRAY + "（对方离开了）");
            grantBattleExp(winner, b, winner.equals(b.p1) ? b.lv2 : b.lv1);
        }
    }

    public void startBattle(Player challenger, Player target) {
        if (!plugin.getManager().hasSummoned(challenger) || !plugin.getManager().hasSummoned(target)) {
            challenger.sendMessage(ChatColor.RED + "双方都必须先 /summon 召唤出宝可梦！");
            return;
        }
        if (isInBattle(challenger) || isInBattle(target)) {
            challenger.sendMessage(ChatColor.RED + "你或对方正在战斗中！");
            return;
        }

        Battle b = new Battle();
        b.p1 = challenger;
        b.p2 = target;
        b.n1 = summonedName(challenger);
        b.n2 = summonedName(target);
        b.lv1 = summonedLevel(challenger);
        b.lv2 = summonedLevel(target);
        b.hp1 = 20 + b.lv1 * 2;
        b.hp2 = 20 + b.lv2 * 2;
        b.turn = challenger.getUniqueId();
        b.expReward = 20 + b.lv2 * 2;

        battles.put(challenger.getUniqueId(), b);
        battles.put(target.getUniqueId(), b);

        target.sendMessage(ChatColor.GOLD + "⚔ " + challenger.getName() + ChatColor.WHITE
                + " 向你发起了宝可梦对战！");
        announceStatus(b);
        turnMsg(b, challenger);
    }

    public void attack(Player p) {
        Battle b = battles.get(p.getUniqueId());
        if (b == null) {
            p.sendMessage(ChatColor.RED + "你没有在对战中！");
            return;
        }
        if (!b.turn.equals(p.getUniqueId())) {
            p.sendMessage(ChatColor.RED + "还没轮到你行动！");
            return;
        }
        boolean isP1 = b.p1.equals(p);
        int lv = isP1 ? b.lv1 : b.lv2;
        int dmg = 3 + lv + plugin.getManager().getRandom().nextInt(5);

        if (isP1) {
            b.hp2 -= dmg;
            b.p2.sendMessage(ChatColor.RED + "你的 " + b.n2 + " 受到了 " + dmg + " 点伤害！");
            b.p2.sendActionBar(ChatColor.RED + "你的 " + b.n2 + " 受到了 " + dmg + " 点伤害！");
        } else {
            b.hp1 -= dmg;
            b.p1.sendMessage(ChatColor.RED + "你的 " + b.n1 + " 受到了 " + dmg + " 点伤害！");
            b.p1.sendActionBar(ChatColor.RED + "你的 " + b.n1 + " 受到了 " + dmg + " 点伤害！");
        }
        p.sendMessage(ChatColor.AQUA + "你的 " + (isP1 ? b.n1 : b.n2)
                + ChatColor.GREEN + " 发动攻击，造成 " + dmg + " 点伤害！");
        p.sendActionBar(ChatColor.AQUA + (isP1 ? b.n1 : b.n2)
                + ChatColor.GREEN + " 发动攻击，造成 " + dmg + " 点伤害！");

        if ((isP1 && b.hp2 <= 0) || (!isP1 && b.hp1 <= 0)) {
            endBattle(b, p);
        } else {
            b.turn = (isP1 ? b.p2 : b.p1).getUniqueId();
            announceStatus(b);
            turnMsg(b, b.p1.equals(p) ? b.p2 : b.p1);
        }
    }

    public void heal(Player p) {
        Battle b = battles.get(p.getUniqueId());
        if (b == null) {
            p.sendMessage(ChatColor.RED + "你没有在对战中！");
            return;
        }
        if (!b.turn.equals(p.getUniqueId())) {
            p.sendMessage(ChatColor.RED + "还没轮到你行动！");
            return;
        }
        boolean isP1 = b.p1.equals(p);
        boolean used = isP1 ? b.heal1 : b.heal2;
        if (used) {
            p.sendMessage(ChatColor.RED + "本场对战中你已经治疗过一次了！");
            return;
        }
        if (isP1) {
            b.heal1 = true;
            b.hp1 = Math.min(20 + b.lv1 * 2, b.hp1 + 12);
            b.p1.sendMessage(ChatColor.GREEN + "你的 " + b.n1 + " 恢复了一些体力！");
        } else {
            b.heal2 = true;
            b.hp2 = Math.min(20 + b.lv2 * 2, b.hp2 + 12);
            b.p2.sendMessage(ChatColor.GREEN + "你的 " + b.n2 + " 恢复了一些体力！");
        }
        b.turn = (isP1 ? b.p2 : b.p1).getUniqueId();
        announceStatus(b);
        turnMsg(b, b.p1.equals(p) ? b.p2 : b.p1);
    }

    private void endBattle(Battle b, Player winner) {
        Player loser = b.p1.equals(winner) ? b.p2 : b.p1;
        winner.sendMessage(ChatColor.GOLD + "★ 对战胜利！"
                + ChatColor.AQUA + (winner.equals(b.p1) ? b.n1 : b.n2)
                + ChatColor.GOLD + " 获得了 " + b.expReward + " 点经验！");
        loser.sendMessage(ChatColor.RED + "你的宝可梦倒下了... " + ChatColor.GOLD + winner.getName() + " 获胜！");
        winner.playSound(winner.getLocation(), Sound.ENTITY_PLAYER_LEVELUP, 1f, 1.2f);
        winner.sendTitle(ChatColor.GOLD + "★ 对战胜利！",
                ChatColor.AQUA + (winner.equals(b.p1) ? b.n1 : b.n2)
                        + ChatColor.GOLD + " 获得 " + b.expReward + " 经验", 10, 60, 20);
        grantBattleExp(winner, b, winner.equals(b.p1) ? b.lv2 : b.lv1);
        battles.remove(b.p1.getUniqueId());
        battles.remove(b.p2.getUniqueId());
    }

    private void grantBattleExp(Player winner, Battle b, int loserLv) {
        plugin.getManager().grantExp(winner, 20 + loserLv * 2);
    }

    private String summonedName(Player p) {
        PokeManager m = plugin.getManager();
        PlayerData pd = m.getData(p);
        for (Pokemon x : pd.getTeam()) {
            if (x.getSpecies() == m.getSummonedEntity(p).getType()) {
                return x.getNickname();
            }
        }
        return "未知宝可梦";
    }

    private int summonedLevel(Player p) {
        PokeManager m = plugin.getManager();
        PlayerData pd = m.getData(p);
        for (Pokemon x : pd.getTeam()) {
            if (x.getSpecies() == m.getSummonedEntity(p).getType()) {
                return x.getLevel();
            }
        }
        return 1;
    }

    private void announceStatus(Battle b) {
        b.p1.sendMessage(ChatColor.WHITE + "[" + ChatColor.AQUA + b.n1
                + ChatColor.GRAY + " " + b.hp1 + "/" + (20 + b.lv1 * 2)
                + ChatColor.WHITE + "  vs  " + ChatColor.RED + b.n2
                + ChatColor.GRAY + " " + b.hp2 + "/" + (20 + b.lv2 * 2) + ChatColor.WHITE + "]");
        b.p2.sendMessage(ChatColor.WHITE + "[" + ChatColor.AQUA + b.n1
                + ChatColor.GRAY + " " + b.hp1 + "/" + (20 + b.lv1 * 2)
                + ChatColor.WHITE + "  vs  " + ChatColor.RED + b.n2
                + ChatColor.GRAY + " " + b.hp2 + "/" + (20 + b.lv2 * 2) + ChatColor.WHITE + "]");
        
        String p1bar = ChatColor.AQUA + b.n1 + ChatColor.GRAY + " " + b.hp1 + "/" + (20 + b.lv1 * 2)
                + ChatColor.WHITE + "  ⚔  " + ChatColor.RED + b.n2 + ChatColor.GRAY + " " + b.hp2 + "/" + (20 + b.lv2 * 2);
        b.p1.sendActionBar(p1bar);
        b.p2.sendActionBar(p1bar);
    }

    private void turnMsg(Battle b, Player turn) {
        String name = b.p1.equals(turn) ? b.n1 : b.n2;
        turn.sendMessage(ChatColor.YELLOW + "轮到你了！输入 /attack 攻击，或 /heal 治疗一次");
        turn.sendActionBar(ChatColor.YELLOW + "轮到你了！/attack 攻击  /heal 治疗");
        Player other = b.p1.equals(turn) ? b.p2 : b.p1;
        other.sendMessage(ChatColor.GRAY + "（轮到对方行动...）");
        other.sendActionBar(ChatColor.GRAY + "（轮到对方行动...）");
    }
}
