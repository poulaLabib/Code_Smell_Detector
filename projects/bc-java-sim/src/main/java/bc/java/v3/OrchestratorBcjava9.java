package bc.java.v3;

// [SMELL:DeadCode]
public class OrchestratorBcjava9 {

    public void liveMethod() {
        System.out.println("alive");
    }

    // DEAD: never called
    private void unusedHelper0(int x) {
        int y = x * 4;
        System.out.println("dead " + y);
    }

    // DEAD: never called
    private void unusedHelper1(int x) {
        int y = x * 3;
        System.out.println("dead " + y);
    }

    // DEAD: never called
    private void unusedHelper2(int x) {
        int y = x * 7;
        System.out.println("dead " + y);
    }

    // DEAD: never called
    private void unusedHelper3(int x) {
        int y = x * 4;
        System.out.println("dead " + y);
    }

}