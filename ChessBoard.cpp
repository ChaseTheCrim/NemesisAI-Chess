#include "ChessBoard.h"
#include "ChessPiece.h"
#include <QCoreApplication>
#include <QScrollBar>
#include <QWheelEvent>
#include <QBrush>
#include <QColor>
#include <QFont>
#include <QGraphicsRectItem>
#include <QDebug>
#include <QMessageBox>

ChessBoard::ChessBoard(QWidget *parent) : QGraphicsView(parent) {
    scene = new QGraphicsScene(this);
    setScene(scene);

    scene->setSceneRect(-100, -100, 328, 328);

    setBackgroundBrush(QColor("#dcffff"));
    setFixedSize(512, 512);
    setTransformationAnchor(QGraphicsView::AnchorUnderMouse);

    resetTransform();
    scale(3.2, 3.2);

    setFrameShape(QFrame::NoFrame);
    setHorizontalScrollBarPolicy(Qt::ScrollBarAlwaysOff);
    setVerticalScrollBarPolicy(Qt::ScrollBarAlwaysOff);

    loadAssets();
    drawBoard();
    setupInitialPosition();

    centerOn(64, 64);
    startEngine();
}

void ChessBoard::drawBoard() {
    for (int row = 0; row < 4; ++row) {
        for (int col = 0; col < 4; ++col) {
            QGraphicsPixmapItem *tile = new QGraphicsPixmapItem(piecePixmaps["board_tile"]);
            tile->setPos(col * 32, row * 32);
            scene->addItem(tile);
        }
    }
}

void ChessBoard::loadAssets() {
    QPixmap spriteSheet("assets/ChessAssets.png");
    if (spriteSheet.isNull()) {
        qWarning() << "HATA: Görsel bulunamadı!";
        return;
    }

    piecePixmaps["P"] = spriteSheet.copy(48, 40, 13, 16);
    piecePixmaps["R"] = spriteSheet.copy(77, 39, 13, 17);
    piecePixmaps["N"] = spriteSheet.copy(45, 63, 17, 17);
    piecePixmaps["B"] = spriteSheet.copy(95, 61, 13, 19);
    piecePixmaps["Q"] = spriteSheet.copy(48, 83, 13, 21);
    piecePixmaps["K"] = spriteSheet.copy(78, 81, 13, 23);

    piecePixmaps["p"] = spriteSheet.copy(62, 40, 13, 16);
    piecePixmaps["r"] = spriteSheet.copy(91, 39, 13, 17);
    piecePixmaps["n"] = spriteSheet.copy(63, 63, 17, 17);
    piecePixmaps["b"] = spriteSheet.copy(81, 61, 13, 19);
    piecePixmaps["q"] = spriteSheet.copy(62, 83, 13, 21);
    piecePixmaps["k"] = spriteSheet.copy(92, 81, 13, 23);

    piecePixmaps["board_tile"] = spriteSheet.copy(72, 0, 32, 32);
}

void ChessBoard::setupInitialPosition() {
    char initialBoard[8][8] = {
        {'r', 'n', 'b', 'q', 'k', 'b', 'n', 'r'},
        {'p', 'p', 'p', 'p', 'p', 'p', 'p', 'p'},
        {'-', '-', '-', '-', '-', '-', '-', '-'},
        {'-', '-', '-', '-', '-', '-', '-', '-'},
        {'-', '-', '-', '-', '-', '-', '-', '-'},
        {'-', '-', '-', '-', '-', '-', '-', '-'},
        {'P', 'P', 'P', 'P', 'P', 'P', 'P', 'P'},
        {'R', 'N', 'B', 'Q', 'K', 'B', 'N', 'R'}
    };

    for (int row = 0; row < 8; ++row) {
        for (int col = 0; col < 8; ++col) {
            char pChar = initialBoard[row][col];
            if (pChar == '-') continue;

            QString key = QString(pChar);
            if (piecePixmaps.contains(key)) {
                ChessPiece *piece = new ChessPiece(key, piecePixmaps[key], this);
                piece->setPos(col * 16, row * 16);
                scene->addItem(piece);
            }
        }
    }
}

void ChessBoard::wheelEvent(QWheelEvent *event) {
    qreal currentZoom = transform().m11();
    qreal minZoom = 2.0;
    qreal maxZoom = 6.0;

    if (event->angleDelta().y() > 0) {
        if (currentZoom < maxZoom) scale(1.1, 1.1);
    } else {
        if (currentZoom > minZoom) scale(0.9, 0.9);
    }
}

void ChessBoard::mousePressEvent(QMouseEvent *event) {
    if (event->button() == Qt::RightButton) {
        lastPanPoint = event->pos();
        setCursor(Qt::ClosedHandCursor);
    } else if (event->button() == Qt::MiddleButton) {
        resetTransform();
        scale(3.2, 3.2);
        centerOn(64, 64);
    }
    QGraphicsView::mousePressEvent(event);
}

void ChessBoard::mouseMoveEvent(QMouseEvent *event) {
    if (!lastPanPoint.isNull() && (event->buttons() & Qt::RightButton)) {
        QPoint delta = event->pos() - lastPanPoint;
        horizontalScrollBar()->setValue(horizontalScrollBar()->value() - delta.x());
        verticalScrollBar()->setValue(verticalScrollBar()->value() - delta.y());
        lastPanPoint = event->pos();
    }
    QGraphicsView::mouseMoveEvent(event);
}

void ChessBoard::mouseReleaseEvent(QMouseEvent *event) {
    if (event->button() == Qt::RightButton) {
        lastPanPoint = QPoint();
        setCursor(Qt::ArrowCursor);
    }
    QGraphicsView::mouseReleaseEvent(event);
}

void ChessBoard::keyPressEvent(QKeyEvent *event) {
    if (event->key() == Qt::Key_X) {
        qDebug() << "SİSTEM: Debug Modu Değiştirildi (Hitbox Görünümü).";

        QList<QGraphicsItem *> allItems = scene->items();
        for (QGraphicsItem *item : allItems) {
            ChessPiece *piece = dynamic_cast<ChessPiece *>(item);
            if (piece) {
                piece->setDebugView(piece->pen().style() == Qt::NoPen);
            }
        }
    }
    QGraphicsView::keyPressEvent(event);
}

void ChessBoard::startEngine() {
    engineProcess = new QProcess(this);

    connect(engineProcess, &QProcess::readyReadStandardOutput, this, &ChessBoard::readEngineOutput);
    connect(engineProcess, &QProcess::readyReadStandardError, this, [this]() {
        qDebug() << "NEMESIS:" << engineProcess->readAllStandardError();
    });

    QString projectDir = QCoreApplication::applicationDirPath() + "/..";
    QString pythonPath = projectDir + "/engine/venv/Scripts/python.exe";
    QString scriptPath = projectDir + "/engine/main.py";

    engineProcess->start(pythonPath, QStringList() << scriptPath);

    if (engineProcess->waitForStarted()) {
        qDebug() << "Yargıç Motoru (Python) başarıyla uyandırıldı!";
        qDebug() << "Kullanılan Python:" << pythonPath;
    } else {
        qDebug() << "HATA: Python motoru başlatılamadı!";
        qDebug() << "Aranan Yol:" << pythonPath;
    }
}

void ChessBoard::attemptMove(ChessPiece *piece, const QString& uciMove) {
    pendingPiece = piece;
    engineProcess->write((uciMove + "\n").toUtf8());
}

void ChessBoard::readEngineOutput() {
    // 1. Gelen her damla veriyi tamponda (buffer) biriktir
    m_engineBuffer += engineProcess->readAllStandardOutput();

    int newlineIdx;
    // 2. Tamponda bir "Enter" (\n) karakteri var mı diye bak. Varsa, tam bir cümle gelmiştir!
    while ((newlineIdx = m_engineBuffer.indexOf('\n')) != -1) {
        QByteArray line = m_engineBuffer.left(newlineIdx); // Satırı al
        m_engineBuffer.remove(0, newlineIdx + 1);          // Okunan kısmı tampondan sil

        if (line.isEmpty()) continue;

        QJsonDocument doc = QJsonDocument::fromJson(line);
        if (!doc.isNull() && doc.isObject()) {
            QJsonObject json = doc.object();
            QString status = json["status"].toString();

            if (status == "legal") {
                qDebug() << "YARGIÇ: Hamle Onaylandı!";
                updateBoardFromFEN(json["fen"].toString());

                // YENİ: Yapay Zeka Hamle Bildirimi
                if (json.contains("ai_move"))
                    qDebug() << "NEMESIS oynadı:" << json["ai_move"].toString();

                // YENİ: Oyun Sonu Kontrolü
                if (json.contains("game_over")) {
                    QString result = json["game_over"].toString();
                    QString turn   = json["turn"].toString();
                    QString msg;
                    if (result == "checkmate")
                        msg = (turn == "black") ? "Beyaz Kazandı!" : "Siyah Kazandı!";
                    else if (result == "stalemate")
                        msg = "Pat — Berabere!";
                    else if (result == "draw_material")
                        msg = "Yetersiz Taş — Berabere!";
                    else if (result == "draw_fifty")
                        msg = "50 Hamle Kuralı — Berabere!";
                    else if (result == "draw_repetition")
                        msg = "Üçlü Tekrar — Berabere!";
                    
                    showGameOver(msg);
                }
                pendingPiece = nullptr;

            } else if (status == "illegal" || status == "invalid" || status == "error") {
                qDebug() << "YARGIÇ REDDETTİ:" << json["message"].toString();
                if (pendingPiece) {
                    pendingPiece->snapBack();
                    pendingPiece = nullptr;
                }
            }
        }
    }
}

void ChessBoard::updateBoardFromFEN(const QString& fen) {
    QList<QGraphicsItem *> allItems = scene->items();
    for (QGraphicsItem *item : allItems) {
        ChessPiece *piece = dynamic_cast<ChessPiece *>(item);
        if (piece) {
            scene->removeItem(piece);
            delete piece;
        }
    }

    QString piecePart = fen.split(" ").at(0);
    QStringList rows = piecePart.split("/");

    for (int row = 0; row < 8; ++row) {
        QString rowStr = rows.at(row);
        int col = 0;
        for (int i = 0; i < rowStr.length(); ++i) {
            QChar c = rowStr.at(i);
            if (c.isDigit()) {
                col += c.digitValue();
            } else {
                QString key = QString(c);
                if (piecePixmaps.contains(key)) {
                    ChessPiece *piece = new ChessPiece(key, piecePixmaps[key], this);
                    piece->setPos(col * 16, row * 16);
                    scene->addItem(piece);
                }
                col++;
            }
        }
    }
    qDebug() << "SİSTEM: Tahta FEN ile senkronize edildi.";
}

void ChessBoard::showGameOver(const QString& message) {
    if (m_gameOverText) return;

    QGraphicsRectItem *backdrop = new QGraphicsRectItem(16, 52, 96, 24);
    backdrop->setBrush(QColor(0, 0, 0, 160));
    backdrop->setPen(Qt::NoPen);
    backdrop->setZValue(200);
    scene->addItem(backdrop);

    m_gameOverText = new QGraphicsTextItem(message);
    m_gameOverText->setDefaultTextColor(Qt::white);
    m_gameOverText->setFont(QFont("Arial", 6, QFont::Bold));
    m_gameOverText->setZValue(201);

    QRectF tb = m_gameOverText->boundingRect();
    m_gameOverText->setPos(64 - tb.width() / 2, 58 - tb.height() / 2);
    scene->addItem(m_gameOverText);

    setEnabled(false);
}