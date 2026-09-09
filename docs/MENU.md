# MENU file description

Each text entry is in `TEXT` encoding, ending with `0xfd`

## 0x0000: Header

Five entries of:

| Offset | Size | Description                             |
| ------ | ---- | --------------------------------------- |
| 0      | 2    | Name pointer                            |
| 2      | 1    | Display row                             |
| 3      | 1    | Name width?                             |
| 4      | 2    | Scenario ID, used for file names        |
| 6      | 2    | ?                                       |
| 8      | 1    | Max party size                          |
| 9      | 1    | Extra ID, used for file names (NC/D/P?) |
| 10     | 6    | ?                                       |

'Name pointer' assumes the MENU data is being loaded at `0x9200`.

## 0x0050: Scenario Names

Five text entries.

## 0x0100, 0x0200, 0x0300, 0x0400, 0x0500: Scenario Descriptions

Several text entries.

## 0x0600, 0x0a00, 0x0e00, 0x1200, 0x1600: Bestiary

TODO First 32 bytes seem to be 16 pointers? To what, who knows; they are the same every time?

One text entry per enemy type?
