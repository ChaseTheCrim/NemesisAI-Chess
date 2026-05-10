#include <QApplication>
#include "ChessBoard.h"

int main(int argc, char *argv[]) {
    QApplication a(argc, argv);
    
    ChessBoard board;
    board.setWindowTitle("Dinamik Satranç Botu");
    board.show();
    
    return a.exec();
}