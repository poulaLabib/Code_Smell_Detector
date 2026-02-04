package bc.java.v1;

import java.util.*;

// [SMELL:Clean]
public class ParserBcjava4 {

    private final List<String> items;

    public ParserBcjava4() { this.items = new ArrayList<>(); }

    public void add(String item) {
        if (item != null && !item.isEmpty()) items.add(item);
    }

    public List<String> getItems() { return Collections.unmodifiableList(items); }
    public int size() { return items.size(); }
    public boolean contains(String item) { return items.contains(item); }
}