using System;
using System.Linq;

class EventLogComparer
{
    // Metoda do konwersji hex do tablicy bajtów
    public static byte[] HexStringToByteArray(string hex)
    {
        return Enumerable.Range(0, hex.Length)
                         .Where(x => x % 2 == 0)
                         .Select(x => Convert.ToByte(hex.Substring(x, 2), 16))
                         .ToArray();
    }

    // Porównanie dwóch tablic bajtów i identyfikowanie nowych eventów
    public static void CompareEventLogs(byte[] log1, byte[] log2)
    {
        const int logLength = 156; // Oczekiwana długość logów

        // Sprawdzenie, czy oba logi mają odpowiednią długość
        if (log1.Length != logLength || log2.Length != logLength)
        {
            Console.WriteLine($"Błąd: Logi muszą mieć długość {logLength} bajtów.");
            return;
        }

        // Przejście przez każdy event w logach, przy założeniu, że każdy event ma 6 bajtów
        for (int i = 0; i < logLength; i += 6)
        {
            byte[] event1 = log1.Skip(i).Take(6).ToArray();
            byte[] event2 = log2.Skip(i).Take(6).ToArray();

            // Porównanie eventów - jeśli są różne, wyświetl event z logu 2
            if (!event1.SequenceEqual(event2))
            {
                Console.WriteLine($"Nowy lub zmieniony event: {BitConverter.ToString(event2)}");
                ParseEvent(event2);
            }
        }
    }

    // Parsowanie zdarzenia
    public static void ParseEvent(byte[] eventBytes)
    {
        if (eventBytes.Length >= 6)
        {
            byte eventCode = eventBytes[4];         // 5 bajt to kod eventu
            byte additionalInfo = eventBytes[5];    // 6 bajt to dodatkowe informacje

            Console.WriteLine($"Event {eventCode:X2} reported with additional info {additionalInfo:X2}");
        }
    }

    static void Main(string[] args)
    {
        // Dane reprezentowane jako ciągi szesnastkowe (hex), które konwertujemy na tablice bajtów
        string log1Hex = "00 00 00 00 00 00 00 00 00 00 FF FF FF FF 00 FF FF FF FF 00 FF FF FF FF 00 FF FF FF FF 00 FF FF FF FF 00 FF FF FF FF 00 FF FF FF FF 00 FF FF FF FF 00 FF FF FF FF 00 FF FF FF FF 00 FF FF FF FF 00 FF FF FF FF 00 FF FF FF FF 00 FF FF FF FF 00 FF FF FF FF 00 FF FF FF FF 00 FF FF FF AD 54 32 11 00 00 00 00 00 00 00 00 00 00";
        string log2Hex = "00 00 00 01 00 00 00 00 00 12 32 1B 02 03 FF FF FF FF 00 FF FF FF FF 00 FF FF FF FF 00 FF FF FF FF 00 FF FF FF FF 00 FF FF FF FF 00 FF FF FF FF 00 FF FF FF FF 00 FF FF FF FF 00 FF FF FF FF 00 FF FF FF FF 00 FF FF FF FF 00 FF FF FF FF 00 FF FF FF AD 54 32 11 00 00 00 00 00 00 00 00 00 00";

        // Konwersja do tablicy bajtów
        byte[] log1 = HexStringToByteArray(log1Hex.Replace(" ", ""));
        byte[] log2 = HexStringToByteArray(log2Hex.Replace(" ", ""));

        // Sprawdzenie, czy oba logi mają długość 156 bajtów
        Console.WriteLine($"Długość log1: {log1.Length} bajtów");
        Console.WriteLine($"Długość log2: {log2.Length} bajtów");

        // Porównanie logów
        CompareEventLogs(log1, log2);
    }
}
